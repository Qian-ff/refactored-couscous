'use strict';
// Read-only with --check. No app imports, network, credentials, native tools or installs.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const root=__dirname,parent=path.dirname(root),check=process.argv.includes('--check');
const approved='7a678db1d3eee3055e0b369bb18952abf1d79676',prefix='others/design/ui-redesign/assistant-floating-v1/';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const json=n=>JSON.parse(fs.readFileSync(path.join(root,n),'utf8'));
const fail=s=>{throw Error(s);};
const a=json('approval.json'),reg=json('registration.json'),qa=json('qa-report.json'),inv=json('inventory.json');
if(a.images_status!=='approved'||a.approved_commit!==approved||a.evidence.answer!=='批准 v1.1，继续规范与 A 交接')fail('Exact image approval missing.');
if(a.evidence.question_item_id!=='["request_user_input_async","call_540ea4383fa7468f9f9e039e50fec5ca",0]')fail('Approval question mismatch.');
if(reg.images_status!=='approved'||reg.approval.approved_commit!==approved||reg.handoff_status!=='ready_for_A')fail('Design handoff registration mismatch.');
if(qa.screens.length!==48||inv.screens.length!==48||new Set(qa.screens.map(x=>x.id)).size!==48)fail('Image coverage mismatch.');
if(!Object.values(qa.checks).every(Boolean)||Object.keys(qa.interaction_checks).length!==20||!Object.values(qa.interaction_checks).every(Boolean))fail('Static QA incomplete.');
if(qa.product_code_changed||qa.native_acceptance||qa.live_business_acceptance)fail('Design evidence must not claim live acceptance.');
for(const [file,digest] of Object.entries(qa.input_sha256))if(sha(fs.readFileSync(path.join(root,file)))!==digest)fail(`Capture source changed: ${file}`);
for(const s of qa.screens){const b=fs.readFileSync(path.join(root,'images',s.filename));if(sha(b)!==s.sha256||b.readUInt32BE(16)!==s.width||b.readUInt32BE(20)!==s.height)fail(`PNG changed: ${s.id}`);}
const old=JSON.parse(fs.readFileSync(path.join(parent,'freeze-manifest.json'),'utf8'));
if(old.files.length!==141)fail('Original UI manifest mismatch.');
for(const f of old.files){const b=fs.readFileSync(path.join(parent,f.file));if(b.length!==f.bytes||sha(b)!==f.sha256)fail(`Original UI modified: ${f.file}`);}
const map=fs.readFileSync(path.join(root,'functional-map.md'),'utf8');for(const s of inv.screens)if(!map.includes(`index.html#${s.id})`))fail(`Unmapped image: ${s.id}`);
const tokens=json('tokens.json');if(tokens.dock.hidden_width!==80||tokens.dock.visible_width!==48||tokens.dock.restore_target_height!==56)fail('Approved edge dimensions changed.');
const expected=[
 '.gitignore','README.md','SOURCES.md','delivery-check.json','design-plan.md','gallery.css','index.html','inventory.json','preview.html','preview.png','prototype.css','prototype.html','prototype.js','qa-report.json','registration.json','render.cjs','state-notes.md','visual-review.md','edge-comparison.html','edge-comparison.png',
 'approval.json','tokens.json','design-spec.md','state-spec.md','platform-spec.md','functional-map.md','handoff.md','acceptance.md','extract-assets.cjs','freeze.cjs','assets/icons.svg',
 'images/web-dialog-detail.png','qa/before-web-dock-left.png','qa/before-mobile-dock-left.png',
 ...inv.screens.map(s=>`images/${s.id}.png`),
];for(let i=1;i<=6;i++)expected.push(`qa/contact-${String(i).padStart(2,'0')}.html`,`qa/contact-${String(i).padStart(2,'0')}.png`);
const unique=Array.from(new Set(expected)).sort();if(unique.length!==expected.length)fail('Duplicate manifest path.');
function walk(dir,relative=''){return fs.readdirSync(dir).flatMap(name=>{const item=path.join(dir,name),rel=relative+name,st=fs.lstatSync(item);if(st.isSymbolicLink())fail(`Symlink disallowed: ${rel}`);if(st.isDirectory()){if(['.runtime','.cache'].includes(name))return [];return walk(item,rel+'/');}if(['freeze-manifest.json','qa-partial.json'].includes(rel))return [];return [rel];});}
const disk=walk(root).sort();if(JSON.stringify(disk)!==JSON.stringify(unique))fail(`Unexpected/missing package files: ${JSON.stringify(disk.filter(x=>!unique.includes(x)).concat(unique.filter(x=>!disk.includes(x))))}`);
const pngs=unique.filter(f=>f.endsWith('.png'));
for(const f of [...pngs,...Object.keys(qa.input_sha256)]){const fromGit=execFileSync('git',['show',`${approved}:${prefix}${f}`],{cwd:root});if(sha(fromGit)!==sha(fs.readFileSync(path.join(root,f))))fail(`Approved bytes changed: ${f}`);}
const svg=fs.readFileSync(path.join(root,'assets/icons.svg'),'utf8');if(/<script|foreignObject|\bon\w+=|(?:href|src)=/i.test(svg)||(svg.match(/<symbol /g)||[]).length!==27)fail('Unexpected exported SVG.');
let localLinks=0;
for(const file of unique.filter(f=>/\.(?:md|html|css)$/.test(f))){
 const text=fs.readFileSync(path.join(root,file),'utf8');let refs=[];
 if(file.endsWith('.html')){refs=Array.from(text.matchAll(/\b(?:href|src)="([^"]+)"/g),m=>m[1]);const ids=Array.from(text.matchAll(/\bid="([^"]+)"/g),m=>m[1]);if(ids.length!==new Set(ids).size)fail(`Duplicate HTML ids: ${file}`);}
 else if(file.endsWith('.css'))refs=Array.from(text.matchAll(/url\(\s*['"]?([^\)'"\s]+)/g),m=>m[1]);
 else refs=Array.from(text.matchAll(/!?\[[^\]]*\]\(([^\n\)]+)\)/g),m=>m[1]);
 for(const ref of refs){if(/^(?:[a-z]+:|\/\/|#)/i.test(ref))continue;const name=decodeURIComponent(ref.split(/[?#]/)[0].replace(/^<|>$/g,''));if(!name)continue;const target=path.resolve(root,path.dirname(file),name);if(!check&&target===path.join(root,'freeze-manifest.json'))continue;if(!fs.existsSync(target)||!fs.statSync(target).isFile())fail(`Broken link: ${file} -> ${ref}`);localLinks++;}
}
const files=unique.map(file=>{const b=fs.readFileSync(path.join(root,file));return {file,bytes:b.length,sha256:sha(b)};});
if(check){const frozen=json('freeze-manifest.json');if(JSON.stringify(frozen.files)!==JSON.stringify(files)||frozen.approved_commit!==approved)fail('Frozen manifest/content mismatch.');}
else fs.writeFileSync(path.join(root,'freeze-manifest.json'),JSON.stringify({schema_version:'labconnect.assistant-freeze/1',version:a.version,frozen_at_utc:new Date().toISOString(),client_date:'2026-10-22',approved_commit:approved,approval:a,primary_images:48,png_files:pngs.length,static_interactions:20,original_ui_files_verified:141,original_ui_manifest_sha256:sha(fs.readFileSync(path.join(parent,'freeze-manifest.json'))),formal_svg_symbols:27,product_source_changed:false,native_tests_performed:false,live_business_acceptance:false,self_hash_excluded:true,files},null,2)+'\n');
console.log(JSON.stringify({version:a.version,status:check?'passed':'manifest_created',files:files.length,primary_images:48,png_files:pngs.length,static_interactions:20,approved_pngs_and_capture_sources_unchanged:true,original_ui_files_verified:141,local_links_checked:localLinks,product_code_changed:false,native_tests_performed:false},null,2));
