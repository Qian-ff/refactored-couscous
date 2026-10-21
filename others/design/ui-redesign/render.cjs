'use strict';
// No install, no app import, no .env access. The server exposes this directory only.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { VERSION, SCREENS } = require('./prototype.js');
const root = __dirname;
const out = path.join(root,'images');
const baseline = '1e1011b4ff2e3c5a66b22492fb87a671e9699584';
const sha = value=>crypto.createHash('sha256').update(value).digest('hex');
const args = process.argv.slice(2);
const only = args.find(a=>a.startsWith('--only='))?.slice(7).split(',');
const serve = args.includes('--serve');
const selected = only ? SCREENS.filter(s=>only.includes(s.id)) : SCREENS;
if(only && selected.length!==only.length)throw new Error('Unknown screen name.');
const esc = value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const mime = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.png':'image/png','.ttf':'font/ttf','.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8'};
function makeServer(){return http.createServer((req,res)=>{
  let file;
  try{const requested=decodeURIComponent(new URL(req.url,'http://localhost').pathname);file=path.resolve(root,'.'+(requested==='/'?'/index.html':requested));}
  catch{res.writeHead(400);res.end();return;}
  const relative=path.relative(root,file);
  if(relative.startsWith('..')||path.isAbsolute(relative)||relative.split(path.sep).some(part=>part.startsWith('.'))){res.writeHead(403);res.end();return;}
  if(!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
  fs.createReadStream(file).pipe(res);
});}
function gallery(){
  const groups=[['公共入口',['login','service-settings','first-password']],['学生学习空间',['student-courses']],['课程与班级',['teacher-courses','admin-courses','class-overview','class-roster','class-requests','class-staff','class-collaborator','class-admin','class-archived']],['组织与账号',['organizations-school','organizations-college','organizations-major','accounts','invitations']],['重要表单与状态',SCREENS.map(s=>s.id).filter(id=>!['login','service-settings','first-password','student-courses','teacher-courses','admin-courses','class-overview','class-roster','class-requests','class-staff','class-collaborator','class-admin','class-archived','organizations-school','organizations-college','organizations-major','accounts','invitations'].includes(id))]];
  const summary=groups.map(([title,ids])=>`<section class="gallery-section"><h2>${esc(title)} <span>${ids.length}</span></h2><div class="gallery-grid">${ids.map(id=>{const s=SCREENS.find(s=>s.id===id);return `<article class="gallery-card" id="${s.id}"><a href="images/${s.id}.png" target="_blank"><img src="images/${s.id}.png" loading="lazy" alt="${esc(s.title)}的桌面设计图"></a><div class="gallery-caption"><div><h3>${esc(s.title)}</h3><p>${esc(s.role)} · 1440px · 示意数据</p></div><a href="prototype.html?screen=${s.id}" target="_blank">查看静态稿 ↗</a></div>${fs.existsSync(path.join(out,`${id}-continued.png`))?`<a class="continued" href="images/${id}-continued.png" target="_blank">查看表单下半部分 ↗</a>`:''}</article>`;}).join('')}</div></section>`).join('');
  fs.writeFileSync(path.join(root,'index.html'),`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>安研通 · 网页设计图册 v1</title><link rel="stylesheet" href="gallery.css"></head><body><header class="gallery-head"><div><p class="gallery-kicker">安研通 · LabConnect</p><h1>把工作放回有序的实验台。</h1><p>网页 UI 候选方案 · ${VERSION} · 实验室轻立体</p></div><div class="gallery-version"><strong>等待网页方案批准</strong><span>保留青蓝主色 · 全部已有页面</span></div></header><main class="gallery-main"><div class="gallery-note"><strong>这些是设计参考图，数据均为合成示例。</strong><span>尚未接入产品或业务接口；不代表功能已迁移。点击图片查看原尺寸，桌面批准后再补移动稿与最终规范。</span></div><nav class="gallery-nav">${groups.map(([title],i)=>`<a href="#section-${i}">${title}</a>`).join('')}</nav>${summary.replaceAll('<section class="gallery-section">',(()=>{let i=0;return()=>`<section class="gallery-section" id="section-${i++}">`;})())}<footer>基线 b1-ready · 契约0.3.1 · 图片与静态来源同版。网页图批准前不修改产品 UI。</footer></main></body></html>`,'utf8');
}
async function run(){
  fs.mkdirSync(out,{recursive:true});
  gallery();
  const server=makeServer();
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin=`http://127.0.0.1:${server.address().port}`;
  if(serve){console.log(`Design gallery only: ${origin}`);return;}
  let browser;
  try{
    const common=execFileSync('git',['rev-parse','--path-format=absolute','--git-common-dir'],{cwd:root,encoding:'utf8'}).trim();
    const primary=path.dirname(common);
    const { chromium } = require(require.resolve('@playwright/test',{paths:[primary]}));
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,reducedMotion:'reduce',locale:'zh-CN',timezoneId:'Asia/Shanghai'});
    const sourceFiles=['prototype.html','prototype.css','prototype.js','assets/fonts/NotoSansSC-VF.ttf','assets/fonts/source.json'];
    const inputs=Object.fromEntries(sourceFiles.map(file=>[file,sha(fs.readFileSync(path.join(root,file)))]));
    const report={version:VERSION,baseline,rendered_at:new Date().toISOString(),desktop_approval:false,production_code_changed:false,width:1440,viewport_height:1000,browser:await browser.version(),input_sha256:inputs,input_fingerprint:sha(JSON.stringify(inputs)),screens:[],blocked_requests:[],browser_errors:[],checks:{font:true,no_horizontal_overflow:true,no_clipped_work_surfaces:true,no_business_requests:true,all_screens_rendered:!only}};
    await context.route('**/*',async route=>{
      const url=route.request().url();
      if(url.startsWith(origin+'/')){await route.continue();return;}
      report.blocked_requests.push(url);await route.abort();
    });
    for(const item of selected){
      const page=await context.newPage();
      page.on('pageerror',e=>report.browser_errors.push({screen:item.id,message:e.message}));
      page.on('console',m=>{if(m.type()==='error')report.browser_errors.push({screen:item.id,message:m.text()});});
      await page.goto(`${origin}/prototype.html?screen=${item.id}`,{waitUntil:'networkidle'});
      await page.evaluate(()=>document.fonts.ready);
      const metrics=await page.evaluate(()=>({
        font:document.fonts.check('16px LabNoto'),
        title:document.title,
        height:document.documentElement.scrollHeight,
        width:document.documentElement.scrollWidth,
        h1:document.querySelector('h1')?.textContent||'',
        unknown:document.body.textContent.includes('未找到设计页面'),
        clipped:Array.from(document.querySelectorAll('.paper,.toolbar,.dialog,.drawer,.catalog-index,.data-table,.course-tile')).filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>({class:e.className,scroll:e.scrollWidth,client:e.clientWidth})),
        broken_links:Array.from(document.querySelectorAll('a[href^="?screen="]')).map(e=>new URL(e.href).searchParams.get('screen')),
        drawerScroll:(()=>{const d=document.querySelector('.drawer-body');return d?d.scrollHeight-d.clientHeight:0;})(),
      }));
      metrics.broken_links=metrics.broken_links.filter(id=>!SCREENS.some(s=>s.id===id));
      const name=`${item.id}.png`;
      await page.screenshot({path:path.join(out,name),fullPage:true,animations:'disabled'});
      const entry={id:item.id,title:item.title,role:item.role,filename:name,width:1440,height:metrics.height,sha256:sha(fs.readFileSync(path.join(out,name))),metrics};
      if(metrics.drawerScroll>4){
        await page.locator('.drawer-body').evaluate(e=>{e.scrollTop=e.scrollHeight;});
        const tail=`${item.id}-continued.png`;
        await page.screenshot({path:path.join(out,tail),fullPage:true,animations:'disabled'});
        entry.continued={filename:tail,sha256:sha(fs.readFileSync(path.join(out,tail)))};
      }
      if(!metrics.font)report.checks.font=false;
      if(metrics.width>1440)report.checks.no_horizontal_overflow=false;
      if(metrics.clipped.length)report.checks.no_clipped_work_surfaces=false;
      if(metrics.unknown||metrics.broken_links.length)throw new Error(`${item.id}: missing page or target: ${metrics.broken_links.join(',')}`);
      report.screens.push(entry);
      await page.close();
    }
    report.checks.no_business_requests=report.blocked_requests.length===0;
    report.checks.no_browser_errors=report.browser_errors.length===0;
    if(!only){
      fs.writeFileSync(path.join(root,'inventory.json'),JSON.stringify({version:VERSION,baseline,screens:SCREENS},null,2)+'\n');
      const map=`# 网页页面与已有功能映射（候选v1）\n\n版本：${VERSION}。所有页面为设计稿、合成数据；用户未批准。现有独立组件随D正式接入，不把本图册当作产品验收。\n\n| 设计稿 | 身份 | 保留功能 | 现有来源 |\n| --- | --- | --- | --- |\n`+SCREENS.map(s=>`| [${s.title}](images/${s.id}.png) | ${s.role} | ${s.features} | ${s.source} |`).join('\n')+'\n';
      fs.writeFileSync(path.join(root,'functional-map.md'),map,'utf8');
    }
    const reportFile=only?'qa-partial.json':'qa-desktop.json';
    fs.writeFileSync(path.join(root,reportFile),JSON.stringify(report,null,2)+'\n');
    gallery();
    if(!only){
      const reviewDir=path.join(root,'qa');fs.mkdirSync(reviewDir,{recursive:true});
      const reviewPage=await context.newPage();
      await reviewPage.setViewportSize({width:1440,height:1200});
      for(let start=0;start<SCREENS.length;start+=9){
        const items=SCREENS.slice(start,start+9);
        await reviewPage.setContent(`<html lang="zh-CN"><head><style>@font-face{font-family:Lab;src:url('${origin}/assets/fonts/NotoSansSC-VF.ttf')}*{box-sizing:border-box}body{margin:0;padding:18px;background:#dfe9ed;color:#172b3a;font:14px/1.6 Lab,sans-serif}h1{font-size:20px;margin:0 0 16px;font-weight:600}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.cell{background:#fff;border:1px solid #bdcfd7;overflow:hidden;border-radius:8px}.cell img{width:100%;display:block}.cell p{margin:0;padding:8px 12px;font-size:12px}.cell span{color:#607482;margin-left:10px}</style></head><body><h1>安研通 · ${VERSION} · 网页设计全页检查 ${start+1}–${start+items.length} · 示意数据</h1><div class="grid">${items.map(s=>`<div class="cell"><img src="${origin}/images/${s.id}.png"><p>${esc(s.title)}<span>${esc(s.role)}</span></p></div>`).join('')}</div></body></html>`,{waitUntil:'networkidle'});
        await reviewPage.evaluate(()=>document.fonts.ready);
        await reviewPage.screenshot({path:path.join(reviewDir,`contact-${String(start/9+1).padStart(2,'0')}.png`),fullPage:true});
      }
      await reviewPage.close();
    }
    console.log(JSON.stringify({version:VERSION,count:report.screens.length,checks:report.checks,errors:report.browser_errors,overflows:report.screens.filter(s=>s.metrics.clipped.length).map(s=>({id:s.id,clipped:s.metrics.clipped})),report:reportFile},null,2));
    if(Object.entries(report.checks).some(([key,value])=>value===false&&(!only||key!=='all_screens_rendered')))process.exitCode=1;
  }finally{if(browser)await browser.close();server.close();}
}
run().catch(error=>{console.error(error.message);process.exitCode=1;});
