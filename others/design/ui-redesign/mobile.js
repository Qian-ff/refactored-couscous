'use strict';
// Visual-only reflow of the approved synthetic desktop canvas. No requests or storage.
const MOBILE_SCREENS = [
  ['m-login','登录','login','','公共入口'],
  ['m-first-password','首次修改密码','first-password','','公共入口'],
  ['m-student','学生课程','student-courses','','学生'],
  ['m-student-menu','学生导航','student-courses','nav','学生'],
  ['m-accounts','账号列表','accounts','','学院管理员'],
  ['m-account-filters','账号筛选','accounts','filters','学院管理员'],
  ['m-account-menu','管理导航','accounts','nav','学院管理员'],
  ['m-account-new','新建学生账号','account-new-student','','学院管理员'],
  ['m-account-grant','账号授权','account-grant','','学校管理员'],
  ['m-role-switch','切换已授权身份','role-switch','','教师兼管理员'],
  ['m-teacher','课程目录与班级','teacher-courses','','教师'],
  ['m-class-roster','班级学生名单','class-roster','','主讲教师'],
  ['m-csv-preview','CSV整批确认','csv-preview','','学院管理员'],
  ['m-csv-errors','CSV错误定位','csv-errors','','学院管理员'],
  ['m-archive','归档确认','class-archive','','主讲教师'],
  ['m-states','全部通用状态','states-sheet','','状态参考'],
].map(([id,title,screen,mode,role])=>({id,title,screen,mode,role,width:390,viewport_height:844,version:'UI-2026.10-v1',synthetic_data:true}));

function mobileReflow(){
  const params=new URLSearchParams(location.search);
  const screen=params.get('screen')||'student-courses';
  const mode=params.get('mode')||'';
  document.body.classList.add('mobile-page');
  const sidebar=document.querySelector('.sidebar');
  const student=screen==='student-courses';
  const topbar=document.querySelector('.topbar');
  if(topbar){
    const previousRole=topbar.querySelector('.role-picker')?.textContent.trim()||'学生';
    const name=topbar.querySelector('.profile-name')?.firstChild?.textContent||'林同学';
    topbar.innerHTML=`<div class="mobile-brand"><span class="mobile-brand-icon">${icon('beaker')}</span><div><strong>安研通</strong><small>示范大学</small></div></div><div class="row gap8">${student?`<span class="mobile-student-name">${name}</span>`:link('role-switch',`${previousRole}${icon('down','sm')}`,'mobile-role-button')}<button type="button" class="mobile-menu-trigger" aria-label="打开导航菜单" aria-expanded="false">${icon('menu')}</button></div>`;
    // Own menu icon, kept separate from the approved icon registry.
    topbar.querySelector('.mobile-menu-trigger').innerHTML='<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16 M4 12h16 M4 18h16"/></svg>';
    const openMenu=()=>{
      if(document.querySelector('.mobile-menu-mask'))return;
      const nav=document.createElement('div');nav.className='mobile-menu-mask';
      nav.innerHTML=`<section class="mobile-nav-sheet" aria-label="导航菜单"><header class="mobile-nav-head"><div><strong>${student?'学习空间':'工作空间'}</strong><p>示范大学 · ${previousRole}</p></div><button class="close" aria-label="关闭导航">${icon('close')}</button></header><div class="mobile-nav-content">${sidebar?.querySelector('nav')?.outerHTML||''}<div class="mobile-nav-scope">${student?'化学学院 · 应用化学':'按当前已授权的学校、学院与教学班范围访问。'}</div></div><footer>${link('login',`${icon('logout','sm')}退出当前账号`,'btn mobile-logout')}</footer></section>`;
      document.body.append(nav);document.body.classList.add('has-overlay');
      const trigger=topbar.querySelector('.mobile-menu-trigger');trigger.setAttribute('aria-expanded','true');
      const close=()=>{nav.remove();trigger.setAttribute('aria-expanded','false');document.body.classList.remove('has-overlay');trigger.focus();};
      nav.querySelector('.close').addEventListener('click',close);
      nav.addEventListener('click',e=>{if(e.target===nav)close();});
      nav.querySelector('.close').focus();
      const escape=e=>{if(e.key==='Escape'){close();document.removeEventListener('keydown',escape);}};
      document.addEventListener('keydown',escape);
    };
    topbar.querySelector('.mobile-menu-trigger').addEventListener('click',openMenu);
    if(mode==='nav')openMenu();
  }
  if(student){
    const intro=document.querySelector('.course-intro');
    if(intro){
      const art=intro.querySelector('.intro-art').innerHTML;
      intro.innerHTML=`<div class="mobile-intro-copy"><span class="intro-subject">${icon('beaker','sm')}实验室安全学习</span><h2>先了解规范，<br>再走进实验室。</h2></div><div class="intro-art">${art}</div><p class="mobile-intro-note">教师发布学习内容后，从对应课程开始学习。</p>`;
    }
    const nav=document.createElement('nav');nav.className='mobile-bottom-nav';nav.setAttribute('aria-label','学生主要导航');
    nav.innerHTML=`${link('student-courses',`${icon('book')}<strong>课程</strong>`,'mobile-bottom-item active')}${[['shield','安全学习'],['voice','学习助手'],['award','培训记录']].map(([i,label])=>`<span class="mobile-bottom-item disabled" aria-disabled="true">${icon(i)}<strong>${label}</strong><small>未开放</small></span>`).join('')}`;
    document.body.append(nav);document.body.classList.add('with-bottom-nav');
    const sectionTitle=document.querySelector('.section-top h2');if(sectionTitle)sectionTitle.innerHTML='已加入的课程 <span class="muted">3</span>';
  }
  // Retain every table field and action; label them explicitly when rows become records.
  document.querySelectorAll('.data-table').forEach(table=>{
    const headers=Array.from(table.querySelectorAll('thead th'),cell=>cell.textContent.trim());
    const records=document.createElement('div');records.className='mobile-records';
    Array.from(table.querySelectorAll('tbody tr')).forEach(row=>{
      const cells=Array.from(row.children);
      const lastAction=/操作|管理|处理/.test(headers[headers.length-1]);
      const item=document.createElement('article');item.className='mobile-record';
      const first=/行号/.test(headers[0])?`<span class="mobile-record-line">CSV 第 ${cells[0].textContent.trim()} 行</span>`:cells[0].innerHTML;
      item.innerHTML=`<div class="mobile-record-title">${first}</div><dl class="mobile-record-data">${cells.slice(1,lastAction?-1:undefined).map((cell,index)=>`<div><dt>${headers[index+1]}</dt><dd>${cell.innerHTML}</dd></div>`).join('')}</dl>${lastAction?`<div class="mobile-record-actions">${cells[cells.length-1].innerHTML}</div>`:''}`;
      records.append(item);
    });
    table.parentElement.replaceWith(records);
  });
  document.querySelectorAll('.toolbar').forEach((toolbar,index)=>{
    const searchField=toolbar.querySelector('.search-field');if(!searchField)return;
    const fields=Array.from(toolbar.querySelectorAll('.field')).filter(el=>el!==searchField);
    const actions=Array.from(toolbar.children).filter(el=>el.matches('.btn'));
    const searchAction=actions.find(el=>/搜索|查询/.test(el.textContent));
    const resetAction=actions.find(el=>/重置|清空/.test(el.textContent));
    const tasks=actions.filter(el=>el!==searchAction&&el!==resetAction);
    toolbar.innerHTML='';
    const row=document.createElement('div');row.className='mobile-search-row';row.append(searchField);if(searchAction)row.append(searchAction);toolbar.append(row);
    if(fields.length){
      const filter=document.createElement('div');filter.className='mobile-filter-body';filter.id=`mobile-filter-${index}`;
      const open=mode==='filters';filter.hidden=!open;
      fields.forEach(f=>filter.append(f));if(resetAction)filter.append(resetAction);
      const toggle=document.createElement('button');toggle.type='button';toggle.className='mobile-filter-toggle';toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-controls',filter.id);toggle.innerHTML=`${icon('settings','sm')}筛选条件 ${icon('down','sm')}`;
      toggle.addEventListener('click',()=>{filter.hidden=!filter.hidden;toggle.setAttribute('aria-expanded',String(!filter.hidden));});
      toolbar.append(toggle,filter);
    }else if(resetAction)toolbar.append(resetAction);
    if(tasks.length){const taskRow=document.createElement('div');taskRow.className='mobile-record-tools';tasks.forEach(el=>taskRow.append(el));toolbar.append(taskRow);}
  });
  const catalog=document.querySelector('.catalog-index');
  if(catalog){
    catalog.classList.add('mobile-catalog','is-collapsed');
    const trigger=document.createElement('button');trigger.type='button';trigger.className='mobile-catalog-trigger';trigger.setAttribute('aria-expanded','false');
    trigger.innerHTML=`<span><small>课程目录</small><strong>${catalog.querySelector('.selected strong')?.textContent||'选择课程目录'}</strong></span>${icon('down','sm')}`;
    catalog.prepend(trigger);trigger.addEventListener('click',()=>{const collapsed=catalog.classList.toggle('is-collapsed');trigger.setAttribute('aria-expanded',String(!collapsed));});
  }
  const auth=document.querySelector('.auth');
  if(auth){const b=document.createElement('div');b.className='mobile-auth-brand';b.innerHTML=brand();auth.prepend(b);}
  const popover=document.querySelector('.popover');
  if(popover){
    const backdrop=document.createElement('div');backdrop.className='backdrop mobile-role-backdrop';
    popover.before(backdrop);backdrop.append(popover);
  }
  if(document.querySelector('.backdrop,.drawer-backdrop,.mobile-menu-mask'))document.body.classList.add('has-overlay');
  document.querySelectorAll('.backdrop,.drawer-backdrop').forEach(el=>{el.querySelector('section')?.setAttribute('aria-modal','true');});
  document.documentElement.dataset.mobileVersion='UI-2026.10-v1';
}
if(typeof module!=='undefined')module.exports={MOBILE_SCREENS};
if(typeof document!=='undefined')mobileReflow();
