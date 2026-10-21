'use strict';
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {MOBILE_SCREENS}=require('./mobile.js');
const {SCREENS}=require('./prototype.js');
const root=__dirname,out=path.join(root,'images-mobile');
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const only=process.argv.find(v=>v.startsWith('--only='))?.slice(7).split(',');
const audit=process.argv.includes('--audit-all');
const selected=audit?SCREENS.map(s=>({id:`audit-${s.id}`,screen:s.id,title:s.title,role:s.role,width:390,viewport_height:844})):only?MOBILE_SCREENS.filter(s=>only.includes(s.id)):MOBILE_SCREENS;
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.png':'image/png','.ttf':'font/ttf'};
function desktopUnchanged(){
  const qa=JSON.parse(fs.readFileSync(path.join(root,'qa-desktop.json'),'utf8'));
  for(const [file,digest]of Object.entries(qa.input_sha256))if(hash(fs.readFileSync(path.join(root,file)))!==digest)throw new Error(`Approved desktop source changed: ${file}`);
  for(const s of qa.screens){
    if(hash(fs.readFileSync(path.join(root,'images',s.filename)))!==s.sha256)throw new Error(`Approved desktop image changed: ${s.id}`);
    if(s.continued&&hash(fs.readFileSync(path.join(root,'images',s.continued.filename)))!==s.continued.sha256)throw new Error(`Approved desktop continuation changed: ${s.id}`);
  }
  return {desktop_commit:'b67ad77cd49c2b5f99d2037e5828c29433ea66a6',desktop_images:55,approved_sources_unchanged:true,approved_images_unchanged:true};
}
function gallery(entries){
  const cards=entries.map(s=>`<article class="mobile-gallery-card"><a href="images-mobile/${s.id}.png" target="_blank"><img src="images-mobile/${s.id}-first.png" alt="${escape(s.title)} 390px设计参考" loading="lazy"></a><div><h2>${escape(s.title)}</h2><p>${escape(s.role)} · 390px · 示意数据</p><a href="images-mobile/${s.id}.png" target="_blank">长页全图</a> · <a href="mobile.html?screen=${s.screen}&mode=${s.mode||''}" target="_blank">静态画布</a>${s.continued?` · <a href="images-mobile/${s.continued.filename}" target="_blank">表单下半部分</a>`:''}</div></article>`).join('');
  fs.writeFileSync(path.join(root,'mobile-gallery.html'),`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>安研通 · 移动设计图册 v1</title><link rel="stylesheet" href="gallery.css"><link rel="stylesheet" href="mobile-gallery.css"></head><body><header class="gallery-head"><div><p class="gallery-kicker">安研通 · LabConnect</p><h1>同一张实验记录页，随屏幕重排。</h1><p>UI-2026.10-v1 · 已批准网页方向的390px补充设计</p></div><div class="gallery-version"><strong>网页v1已获用户批准</strong><span>移动参考与规范交A / 原D接入</span></div></header><main class="gallery-main"><div class="gallery-note"><strong>这是静态设计参考，全部使用合成数据。</strong><span>首屏图展示固定导航和弹窗；长页全图为阅读方便将学生底栏放在页尾。未连接真实接口，未进行原生键盘、系统返回或三端运行验收。</span></div><nav class="gallery-nav"><a href="index.html">网页图册</a><a href="design-spec.md">设计规范</a><a href="platform-spec.md">三端适配</a><a href="handoff.md">迁移交接</a></nav><div class="mobile-gallery-grid">${cards}</div></main></body></html>`,'utf8');
}
async function run(){
  const frozen=desktopUnchanged();fs.mkdirSync(out,{recursive:true});
  const server=http.createServer((req,res)=>{
    let file;try{file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));}catch{res.writeHead(400);res.end();return;}
    const relative=path.relative(root,file);
    if(relative.startsWith('..')||path.isAbsolute(relative)||relative.split(path.sep).some(v=>v.startsWith('.'))||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});fs.createReadStream(file).pipe(res);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
  let browser;
  try{
    const common=execFileSync('git',['rev-parse','--path-format=absolute','--git-common-dir'],{cwd:root,encoding:'utf8'}).trim();
    const {chromium}=require(require.resolve('@playwright/test',{paths:[path.dirname(common)]}));
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true,locale:'zh-CN',timezoneId:'Asia/Shanghai',reducedMotion:'reduce'});
    const inputFiles=['mobile.html','mobile.css','mobile.js','prototype.html','prototype.css','prototype.js','assets/fonts/NotoSansSC-VF.ttf','assets/fonts/source.json','render-mobile.cjs'];
    const inputs=Object.fromEntries(inputFiles.map(file=>[file,hash(fs.readFileSync(path.join(root,file)))]));
    const report={version:'UI-2026.10-v1',rendered_at:new Date().toISOString(),width:390,viewport_height:844,browser:await browser.version(),desktop_approval:JSON.parse(fs.readFileSync(path.join(root,'approval.json'),'utf8')),frozen_desktop:frozen,input_sha256:inputs,input_fingerprint:hash(JSON.stringify(inputs)),screens:[],errors:[],blocked_requests:[],checks:{font:true,no_page_horizontal_overflow:true,no_work_surface_clipping:true,no_missing_table_fields:true,touch_targets_44px:true,no_browser_errors:true,no_business_requests:true,desktop_unchanged:true},native_tests_performed:false};
    await context.route('**/*',async route=>{if(route.request().url().startsWith(origin+'/'))await route.continue();else{report.blocked_requests.push(route.request().url());await route.abort();}});
    for(const s of selected){
      const page=await context.newPage();
      page.on('pageerror',e=>report.errors.push({id:s.id,message:e.message}));
      page.on('console',m=>{if(m.type()==='error')report.errors.push({id:s.id,message:m.text()});});
      await page.goto(`${origin}/prototype.html?screen=${s.screen}`,{waitUntil:'networkidle'});
      const originalRows=await page.locator('.data-table tbody tr').evaluateAll(rows=>rows.map(row=>Array.from(row.children,cell=>cell.textContent.replace(/\s+/g,'').trim())));
      await page.goto(`${origin}/mobile.html?screen=${s.screen}&mode=${s.mode||''}`,{waitUntil:'networkidle'});
      await page.evaluate(()=>document.fonts.ready);
      const metrics=await page.evaluate(()=>{
        const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden';};
        return {
          font:document.fonts.check('16px LabNoto'),width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
          records:Array.from(document.querySelectorAll('.mobile-record'),e=>e.textContent.replace(/\s+/g,'').trim()),
          clipped:Array.from(document.querySelectorAll('.mobile-record,.form-grid,.dialog,.drawer,.toolbar,.course-tile,.mobile-nav-sheet')).filter(visible).filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>({class:e.className,width:e.clientWidth,scroll:e.scrollWidth})),
          small_targets:Array.from(document.querySelectorAll('a,button,input,select,textarea')).filter(visible).filter(e=>!e.disabled).map(e=>({text:(e.textContent||e.getAttribute('aria-label')||e.tagName).trim().slice(0,32),rect:e.getBoundingClientRect()})).filter(v=>v.rect.height<43.5||v.rect.width<43.5).map(v=>({text:v.text,w:Math.round(v.rect.width),h:Math.round(v.rect.height)})),
          scroll_region:(()=>{const el=document.querySelector('.drawer-body,.dialog-body');return el?{selector:el.classList.contains('drawer-body')?'.drawer-body':'.dialog-body',overflow:el.scrollHeight-el.clientHeight}:null;})(),
          bottom_nav:document.querySelector('.mobile-bottom-nav')?{top:document.querySelector('.mobile-bottom-nav').getBoundingClientRect().top,bottom:document.querySelector('.mobile-bottom-nav').getBoundingClientRect().bottom}:null,
        };
      });
      metrics.missing_fields=[];
      originalRows.forEach((cells,index)=>cells.forEach(cell=>{if(cell&&!metrics.records[index]?.includes(cell))metrics.missing_fields.push({row:index,cell});}));
      if(originalRows.length!==metrics.records.length)metrics.missing_fields.push({expected_rows:originalRows.length,actual_rows:metrics.records.length});
      const entry={...s,height:metrics.height,metrics};
      if(!audit){
        await page.screenshot({path:path.join(out,`${s.id}-first.png`),fullPage:false,animations:'disabled'});
        await page.evaluate(()=>{document.documentElement.dataset.capture='full';});
        await page.screenshot({path:path.join(out,`${s.id}.png`),fullPage:true,animations:'disabled'});
        await page.evaluate(()=>{delete document.documentElement.dataset.capture;});
        entry.filename=`${s.id}.png`;entry.sha256=hash(fs.readFileSync(path.join(out,`${s.id}.png`)));entry.first={filename:`${s.id}-first.png`,sha256:hash(fs.readFileSync(path.join(out,`${s.id}-first.png`)))};
      }
      if(!audit&&metrics.scroll_region?.overflow>3){
        await page.locator(metrics.scroll_region.selector).evaluate(e=>{e.scrollTop=e.scrollHeight;});
        const name=`${s.id}-continued.png`;await page.screenshot({path:path.join(out,name),animations:'disabled'});entry.continued={filename:name,sha256:hash(fs.readFileSync(path.join(out,name)))};
      }
      if(!metrics.font)report.checks.font=false;
      if(metrics.width>390)report.checks.no_page_horizontal_overflow=false;
      if(metrics.clipped.length)report.checks.no_work_surface_clipping=false;
      if(metrics.missing_fields.length)report.checks.no_missing_table_fields=false;
      if(metrics.small_targets.length)report.checks.touch_targets_44px=false;
      // Browser viewport-resize and synthetic safe-area checks are not native keyboard/device tests.
      if(s.id==='m-account-new'){
        await page.setViewportSize({width:390,height:520});await page.evaluate(()=>{document.documentElement.dataset.simSafe='true';});
        await page.locator('.drawer-body input').last().scrollIntoViewIfNeeded();
        entry.small_viewport=await page.evaluate(()=>{const f=document.querySelector('.drawer-footer').getBoundingClientRect(),i=Array.from(document.querySelectorAll('.drawer-body input')).at(-1).getBoundingClientRect();return {height:innerHeight,footer_bottom:f.bottom,footer_top:f.top,input_bottom:i.bottom,safe_area_simulated:24};});
        if(entry.small_viewport.footer_bottom>521||entry.small_viewport.input_bottom>entry.small_viewport.footer_top+1)report.errors.push({id:s.id,message:'Small viewport input/footer overlap'});
      }
      report.screens.push(entry);await page.close();
    }
    report.checks.no_browser_errors=report.errors.length===0;report.checks.no_business_requests=report.blocked_requests.length===0;
    desktopUnchanged();
    fs.writeFileSync(path.join(root,audit?'responsive-audit.json':only?'qa-mobile-partial.json':'qa-mobile.json'),JSON.stringify(report,null,2)+'\n');
    if(!only&&!audit){fs.writeFileSync(path.join(root,'mobile-inventory.json'),JSON.stringify({version:report.version,screens:MOBILE_SCREENS},null,2)+'\n');gallery(report.screens);}
    console.log(JSON.stringify({count:report.screens.length,checks:report.checks,errors:report.errors,issues:report.screens.filter(s=>s.metrics.clipped.length||s.metrics.small_targets.length||s.metrics.missing_fields.length).map(s=>({id:s.id,clipped:s.metrics.clipped,small_targets:s.metrics.small_targets,missing:s.metrics.missing_fields}))},null,2));
    if(Object.values(report.checks).some(v=>!v))process.exitCode=1;
  }finally{if(browser)await browser.close();server.close();}
}
run().catch(e=>{console.error(e.message);process.exitCode=1;});
