'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=__dirname,sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
const check=process.argv.includes('--check');
function fail(message){throw new Error(message);}
const approval=read('approval.json'),desktop=read('qa-desktop.json'),mobile=read('qa-mobile.json'),audit=read('responsive-audit.json');
if(approval.desktop_status!=='approved'||approval.desktop_commit!=='b67ad77cd49c2b5f99d2037e5828c29433ea66a6')fail('Missing exact desktop approval.');
if(desktop.screens.length!==53||mobile.screens.length!==16||audit.screens.length!==53)fail('Coverage count mismatch.');
for(const [kind,report]of [['desktop',desktop],['mobile',mobile],['audit',audit]]){
  if(!Object.values(report.checks).every(Boolean))fail(`${kind}: required checks failed.`);
  for(const [file,digest]of Object.entries(report.input_sha256))if(sha(fs.readFileSync(path.join(root,file)))!==digest)fail(`${kind}: changed input ${file}`);
}
const font=read('assets/fonts/source.json');
if(sha(fs.readFileSync(path.join(root,'assets/fonts/NotoSansSC-VF.ttf')))!==font.sha256)fail('Font provenance mismatch.');
const required=[
  '.gitignore','README.md','SOURCES.md','approval.json','registration.json','design-plan.md','mobile-plan.md','design-spec.md','state-spec.md','platform-spec.md','migration-checklist.md','functional-map.md','migration-notes-draft.md','handoff.md','tokens.json','visual-review.md','mobile-review.md',
  'prototype.html','prototype.css','prototype.js','mobile.html','mobile.css','mobile.js','gallery.css','index.html','mobile-gallery.css','mobile-gallery.html','inventory.json','mobile-inventory.json','qa-desktop.json','qa-mobile.json','responsive-audit.json','render.cjs','render-mobile.cjs','extract-assets.cjs','freeze.cjs',
  'assets/fonts/NotoSansSC-VF.ttf','assets/fonts/source.json','assets/fonts/OFL.txt','assets/icons.svg','assets/illustrations/lab-bench.svg','assets/illustrations/chemistry.svg','assets/illustrations/electrical.svg','assets/illustrations/personal-protection.svg',
];
for(let i=1;i<=6;i++)required.push(`qa/contact-${String(i).padStart(2,'0')}.png`);
for(const s of desktop.screens){
  const file=`images/${s.filename}`;if(sha(fs.readFileSync(path.join(root,file)))!==s.sha256)fail(`Desktop image changed ${file}`);required.push(file);
  if(s.continued){const file=`images/${s.continued.filename}`;if(sha(fs.readFileSync(path.join(root,file)))!==s.continued.sha256)fail(`Desktop continuation changed ${file}`);required.push(file);}
}
for(const s of mobile.screens){
  for(const item of [{filename:s.filename,sha256:s.sha256},s.first,s.continued].filter(Boolean)){
    const file=`images-mobile/${item.filename}`;if(sha(fs.readFileSync(path.join(root,file)))!==item.sha256)fail(`Mobile image changed ${file}`);required.push(file);
  }
}
const files=Array.from(new Set(required)).sort().map(file=>({file,bytes:fs.statSync(path.join(root,file)).size,sha256:sha(fs.readFileSync(path.join(root,file)))}));
if(check){
  const frozen=read('freeze-manifest.json');
  if(JSON.stringify(frozen.files)!==JSON.stringify(files))fail('Frozen file set or content changed.');
  console.log(JSON.stringify({version:frozen.version,files:files.length,desktop_images:55,mobile_reference_screens:16,audited_mobile_canvases:53,check:'passed',product_code_changed:false},null,2));
}else{
  fs.writeFileSync(path.join(root,'freeze-manifest.json'),JSON.stringify({version:'UI-2026.10-v1',frozen_at_utc:new Date().toISOString(),desktop_approval:approval,desktop_reference_screens:53,desktop_images:55,mobile_reference_screens:16,mobile_images:36,audited_mobile_canvases:53,native_tests_performed:false,production_code_changed:false,files,self_hash_excluded:true},null,2)+'\n');
  console.log(`Frozen ${files.length} files. Exact Git SHA will be reported after commit.`);
}
