'use strict';
// Isolated visual reference. Synthetic data only; no product imports or requests.
const VERSION = 'UI-2026.10-v1';
const SCREENS = [
  ['login','登录','公共入口','web/src/App.tsx','学校、账号、密码；连接设置；登录失败反馈'],
  ['login-error','登录失败反馈','公共入口','web/src/App.tsx','保留学校与账号输入、错误提示、不泄露账号是否存在'],
  ['service-settings','服务连接设置','公共入口','web/src/App.tsx','服务地址修改、保存前校验、返回登录'],
  ['first-password','首次修改密码','公共入口','web/src/features/teaching/dev/harness.tsx','临时密码、8–256位规则、必须改密、重新登录'],
  ['student-courses','我的课程','学生','web/src/App.tsx','授权课程、搜索、刷新、待开放学习入口'],
  ['teacher-courses','课程与教学班','教师','web/src/features/teaching/CoursesPage.tsx','课程目录、新建课程、已有目录开班、范围搜索'],
  ['courses-history','历史教学班','教师','web/src/features/teaching/CoursesPage.tsx','已归档筛选、恢复在用目录、历史班级独立权限'],
  ['admin-courses','课程管理','学院管理员','web/src/features/teaching/CoursesPage.tsx','目录归属、编辑、归档、开班、目录权限与班级权限区分'],
  ['organizations-school','学校管理','平台运维','web/src/features/admin/OrganizationsPage.tsx','学校新增、编辑、搜索、启停'],
  ['organizations-college','学院管理','学校管理员','web/src/features/admin/OrganizationsPage.tsx','本校学院新增、编辑、搜索、启停'],
  ['organizations-major','专业管理','学院管理员','web/src/features/admin/OrganizationsPage.tsx','授权学院内专业新增、编辑、搜索、启停'],
  ['accounts','账号与授权','学院管理员','web/src/features/admin/AccountsPage.tsx','搜索筛选、新建、编辑、密码重置、批量导入'],
  ['account-new-student','新建学生账号','学院管理员','web/src/features/admin/forms.tsx','独立账号与学号、学院专业、可选资料、学生身份互斥'],
  ['account-edit-student','编辑学生账号','学院管理员','web/src/features/admin/forms.tsx','账号只读、保留学号专业、资料编辑、状态与重置入口'],
  ['account-new-teacher','新建教职账号','学校管理员','web/src/features/admin/forms.tsx','教师兼管理员、可选专业学号、初始临时密码'],
  ['account-edit-teacher','教师身份与授权','学校管理员','web/src/features/admin/forms.tsx','教师兼管理员、学院范围、启停、保留账号标识'],
  ['account-reset','重置密码确认','学院管理员','web/src/features/admin/AccountsPage.tsx','临时密码、撤销全部会话、首次强制改密'],
  ['account-grant','新增角色授权','学校管理员','web/src/features/admin/AccountsPage.tsx','授权角色、学院范围、撤销授权、重新判权'],
  ['account-status','停用账号确认','学院管理员','web/src/features/admin/AccountsPage.tsx','撤销会话、主讲需先交接、停用与重新启用'],
  ['invitations','学生账号邀请','学院管理员','web/src/features/admin/InvitationsPage.tsx','专业范围、有效期、使用次数、创建、撤销'],
  ['invite-issued','新邀请凭据','学院管理员','web/src/features/admin/InvitationsPage.tsx','新建时一次展示邀请码；列表不回显明文'],
  ['class-overview','教学班概览','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','归属信息、设置、邀请码、转交、归档'],
  ['class-roster','学生名单','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','搜索、拉入、移出、批量导入、成员状态'],
  ['class-requests','加入与退出审批','协作教师','web/src/features/teaching/ClassManagementPage.tsx','待审请求、同意、拒绝、请求状态'],
  ['class-staff','教师协作','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','加入协作教师、移除、主讲区别、授权范围'],
  ['class-collaborator','协作教师视角','协作教师','web/src/features/teaching/ClassManagementPage.tsx','名单与审批可操作；关键设置、教师管理、转交归档受限'],
  ['class-staff-readonly','协作教师查看关系','协作教师','web/src/features/teaching/ClassManagementPage.tsx','可查看历史教师关系；无增加、移除、恢复与转交操作'],
  ['class-admin','管理员班级视角','学院管理员','web/src/features/teaching/ClassManagementPage.tsx','范围授权、班级管理、管理员不冒充教师'],
  ['class-archived','已归档教学班','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','归档只读、保留历史、停止加入和修改'],
  ['class-edit','班级名称与审批设置','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','班级名称、加入审批、退出审批、修订校验'],
  ['class-add-member','拉入学生','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','精确本校学生登录账号、无其他学院学生目录'],
  ['class-add-staff','添加协作教师','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','本校教师搜索、最小候选资料、明确选择与授课范围'],
  ['class-joincode','生成班级邀请码','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','有效期、生成新凭据、旧码失效、仅本次明文'],
  ['class-transfer','转交主讲教师','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','同校候选教师、影响提示、二次确认'],
  ['class-archive','归档确认','主讲教师','web/src/features/teaching/ClassManagementPage.tsx','归档影响、明确对象与确认'],
  ['csv-input','CSV内容编辑','学院管理员','web/src/features/teaching/CsvImporter.tsx','文件与文本编辑、模板、文件限制、修改后重做预检'],
  ['csv-input-roster','CSV班级名单编辑','主讲教师','web/src/features/teaching/CsvImporter.tsx','固定班级、文件读取、原始文本编辑、预检'],
  ['csv-preview','CSV预检通过','学院管理员','web/src/features/teaching/CsvImporter.tsx','模板、文件限制、全量预检、原子提交'],
  ['csv-roster','批量加入班级','主讲教师','web/src/features/teaching/CsvImporter.tsx','班级固定范围、引用已开通学生、全量预检、原子提交'],
  ['csv-errors','CSV预检错误','学院管理员','web/src/features/teaching/CsvImporter.tsx','定位行与字段、错误全览、禁止部分写入'],
  ['csv-uncertain','提交结果待确认','学院管理员','web/src/features/teaching/CsvImporter.tsx','响应丢失、保留原请求、同一幂等键重试'],
  ['new-course-teacher','教师新建课程','教师','web/src/App.tsx; web/src/features/teaching/CoursesPage.tsx','目录与首班一起创建、首班本人主讲、学院范围'],
  ['new-course-admin','管理员新建课程','学校管理员','web/src/App.tsx; web/src/features/teaching/CoursesPage.tsx','学院与教师选择、目录与首班创建、权限校验'],
  ['existing-catalog-new-class','已有课程目录开班','课程目录所有者','web/src/features/teaching/CoursesPage.tsx','可指定同校其他主讲、开班后不默认获得该班访问权'],
  ['edit-catalog','编辑课程目录','学院管理员','web/src/features/teaching/CoursesPage.tsx','编码只读、标题、所有者、修订版本、归档与恢复'],
  ['organization-edit','编辑与停用组织','学校管理员','web/src/features/admin/OrganizationsPage.tsx','不可变所属学校、组织名称、启停影响'],
  ['organization-edit-school','编辑与停用学校','平台运维','web/src/features/admin/OrganizationsPage.tsx','学校编码只读、名称、停用后的全校访问影响'],
  ['organization-edit-major','编辑与停用专业','学院管理员','web/src/features/admin/OrganizationsPage.tsx','学校学院归属只读、名称、状态、历史保留'],
  ['organization-new','新建组织','平台运维','web/src/features/admin/OrganizationsPage.tsx','编码、名称、组织层级与范围'],
  ['organization-new-college','新建学院','学校管理员','web/src/features/admin/forms.tsx','学校范围、编码、名称'],
  ['organization-new-major','新建专业','学院管理员','web/src/features/admin/forms.tsx','学校与学院范围、编码、名称'],
  ['role-switch','切换已授权身份','教师兼学院管理员','web/src/features/admin/scope.ts; web/src/features/teaching/dev/harness.tsx','只显示已有授权身份、缩小权限范围、学生无角色切换'],
  ['states-sheet','状态样式总览','状态规范草案','web/src/App.tsx; web/src/features/teaching/ui.tsx','加载、空、失败重试、离线、无权限、修订冲突、未配置、未开放'],
].map(([id,title,role,source,features])=>({id,title,role,source,features,width:1440,status:'design-draft',synthetic_data:true}));

const paths = {
  shield:'M12 3 20 6v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z M8.5 12l2.3 2.3 4.7-5',
  beaker:'M9 3h6 M10 3v6L5 18c-.7 1.3 0 3 1.6 3h10.8c1.6 0 2.3-1.7 1.6-3l-5-9V3 M8 15h8',
  book:'M4 4h6a3 3 0 0 1 2 1 3 3 0 0 1 2-1h6v15h-6a3 3 0 0 0-2 1 3 3 0 0 0-2-1H4V4Z M12 5v15',
  people:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.9 M16 3.1a4 4 0 0 1 0 7.8',
  building:'M4 21V7l8-4 8 4v14 M2 21h20 M8 8v2 M12 8v2 M16 8v2 M8 13v2 M12 13v2 M16 13v2 M10 21v-3h4v3',
  user:'M20 21v-2a7 7 0 0 0-14 0v2 M13 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
  mail:'M3 5h18v14H3V5Z M3 6l9 7 9-7',
  chevron:'m9 5 7 7-7 7', down:'m6 9 6 6 6-6', plus:'M12 5v14 M5 12h14',
  search:'M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15 M16 16l5 5',
  refresh:'M20 7a9 9 0 0 0-15-1L2 9 M2 3v6h6 M4 17a9 9 0 0 0 15 1l3-3 M22 21v-6h-6',
  lock:'M5 10h14v11H5V10Z M8 10V7a4 4 0 0 1 8 0v3 M12 14v3',
  globe:'M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0 M3 12h18 M12 3c4 4 4 14 0 18 M12 3c-4 4-4 14 0 18',
  eye:'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z M15 12a3 3 0 1 0-6 0 3 3 0 0 0 6 0',
  arrow:'M4 12h15 m-6-6 6 6-6 6', back:'M20 12H5 m6-6-6 6 6 6',
  settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3Z',
  logout:'M9 4H4v16h5 M10 12h11 m-4-4 4 4-4 4',
  check:'m5 12 4 4L19 6', close:'m6 6 12 12 M18 6 6 18', info:'M12 8h.01 M12 11v6 M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0',
  warning:'M12 3 2 21h20L12 3Z M12 9v5 M12 17h.01',
  cloud:'M7 18H5a4 4 0 1 1 1-7.9 6 6 0 0 1 11.6-1.5A5 5 0 0 1 19 18h-2 M12 13v8 m-3-3 3 3 3-3',
  upload:'M12 16V3 m-5 5 5-5 5 5 M4 14v6h16v-6',
  download:'M12 3v13 m-5-5 5 5 5-5 M4 15v6h16v-6',
  file:'M5 2h9l5 5v15H5V2Z M14 2v6h5 M8 12h8 M8 16h8',
  edit:'m15 4 5 5-11 11-6 1 1-6L15 4Z M13 6l5 5',
  archive:'M3 3h18v5H3V3Z M5 8v13h14V8 M9 12h6',
  clock:'M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0 M12 7v5l3 2',
  calendar:'M4 5h16v16H4V5Z M7 2v6 M17 2v6 M4 10h16',
  copy:'M9 8h12v13H9V8Z M5 16H3V3h12v2', key:'M14 9a5 5 0 1 0-2 4l9-9-2-2-3 3 2 2',
  wifi:'M3 8a15 15 0 0 1 18 0 M6 12a10 10 0 0 1 12 0 M9 16a5 5 0 0 1 6 0 M12 20h.01',
  more:'M5 12h.01 M12 12h.01 M19 12h.01', award:'M8 14 6 22l6-3 6 3-2-8 M18 8a6 6 0 1 0-12 0 6 6 0 0 0 12 0',
  voice:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5Z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8',
};
function icon(name,cls=''){return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.book}"/></svg>`;}
function brand(){return `<div class="brand"><span class="brand-mark">${icon('beaker')}</span><div><span class="brand-name">安研通</span><span class="brand-en">LabConnect</span></div></div>`;}
function link(screen,label,cls=''){return `<a class="${cls}" href="?screen=${screen}">${label}</a>`;}
function btn(label,kind='',symbol='',screen=''){const text=`${symbol?icon(symbol,'sm'):''}${label}`;return screen?link(screen,text,`btn ${kind}`):`<button type="button" class="btn ${kind}">${text}</button>`;}
function disabled(label){return `<button type="button" class="btn" disabled>${label}</button>`;}
function tag(text,kind=''){return `<span class="tag ${kind}">${text}</span>`;}
function check(label,on=true,disabledState=false){return `<div class="checkbox"><span class="check-box ${on?'checked':''} ${disabledState?'disabled':''}">${on?icon('check'):''}</span>${label}</div>`;}
function toggle(on=true){return `<span class="switch ${on?'on':''}" aria-hidden="true"><i></i></span>`;}
function field(label,value='',hint='',mode='input',extra=''){let control='';if(mode==='select')control=`<div class="control select">${value}${icon('down','sm')}</div>`;else if(mode==='readonly')control=`<div class="control readonly">${value}</div>`;else if(mode==='area')control=`<div class="control area">${value}</div>`;else control=`<input class="control ${mode==='error'?'error':''}" value="${value}" readonly aria-label="${label.replace('*','')}"${mode==='password'?' type="password"':''}>`;return `<div class="field ${extra}"><label>${label}</label>${control}${hint?`<small>${hint}</small>`:''}</div>`;}
function search(placeholder='搜索名称或编码'){return `<div class="field search-field"><div class="control search">${icon('search','sm')}<span>${placeholder}</span></div></div>`;}
function notice(text,kind='',symbol='info'){return `<div class="notice ${kind}">${icon(symbol,'sm')}<div>${text}</div></div>`;}
function person(name,sub='',tone=''){return `<div class="person"><span class="avatar ${tone}">${name[0]}</span><div><strong>${name}</strong>${sub?`<small>${sub}</small>`:''}</div></div>`;}
function table(head,rows){return `<div class="table-wrap"><table class="data-table"><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function pagination(n){return `<div class="pagination"><span>共 ${n} 条 · 每页 10 条</span><div class="pages"><button class="page-num muted" disabled>‹</button><button class="page-num active">1</button><button class="page-num muted" disabled>›</button></div></div>`;}
function head(title,sub,actions=''){return `<div class="page-head"><div><h1>${title}</h1><p>${sub}</p></div><div class="row gap8">${actions}</div></div>`;}
function paper(title,sub,body,actions=''){return `<section class="paper"><div class="paper-header"><div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${actions}</div>${body}</section>`;}
function modal(title,sub,body,footer='',cls=''){return `<div class="backdrop"><section class="dialog ${cls}" aria-label="${title}"><div class="dialog-header"><div><h2>${title}</h2><p>${sub}</p></div><button class="close" aria-label="关闭">${icon('close')}</button></div><div class="dialog-body">${body}</div><div class="dialog-footer">${footer||btn('取消')+btn('保存','primary')}</div></section></div>`;}
function drawer(title,sub,body,footer=''){return `<div class="drawer-backdrop"><section class="drawer" aria-label="${title}"><div class="dialog-header"><div><h2>${title}</h2><p>${sub}</p></div><button class="close" aria-label="关闭">${icon('close')}</button></div><div class="drawer-body">${body}</div><div class="drawer-footer">${footer||btn('取消')+btn('保存修改','primary')}</div></section></div>`;}

let artCounter=0;
function labArt(kind='bench'){
  const u=`a${++artCounter}`;
  const defs=`<defs><linearGradient id="${u}glass" x1="0" x2="1"><stop stop-color="#d6edf0" stop-opacity=".8"/><stop offset=".4" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#9dc9d5" stop-opacity=".65"/></linearGradient><linearGradient id="${u}liquid" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#5ebdc5"/><stop offset="1" stop-color="#087f8c"/></linearGradient><linearGradient id="${u}blue" x1="0" x2="1"><stop stop-color="#6997d9"/><stop offset="1" stop-color="#315f9c"/></linearGradient><linearGradient id="${u}body" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff"/><stop offset="1" stop-color="#d6e5e9"/></linearGradient></defs>`;
  const bench=`<ellipse cx="290" cy="300" rx="223" ry="32" fill="#46758a" opacity=".1"/><path d="m54 257 304-62 162 75-301 67Z" fill="#d9e8ed"/><path d="m54 257 165 69 301-56v18l-301 59-165-70Z" fill="#adcbd5"/><path d="m54 257 165 69v21l-165-70Z" fill="#c6dce3"/><path d="m54 257 304-62 162 75-301 56Z" fill="#fff" stroke="#cedfe5" stroke-width="2"/>`;
  const flask=`<g><path d="M197 85v71l-44 78c-8 15 1 29 20 32 31 5 58 2 82-4 14-4 18-17 10-30l-42-76V85Z" fill="url(#${u}glass)" stroke="#8bb7c5" stroke-width="2"/><path d="m175 208-16 29c-6 12 3 21 17 23 28 4 54 2 75-3 10-3 13-11 7-21l-16-28c-17 5-43 6-67 0Z" fill="url(#${u}liquid)"/><ellipse cx="208" cy="208" rx="33" ry="6" fill="#85cdd0"/><ellipse cx="210" cy="85" rx="15" ry="5" fill="#e9f7f8" stroke="#8bb7c5" stroke-width="2"/><path d="M203 100v60l-30 56" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".8"/><path d="M234 210h13 M239 223h14 M244 237h12" stroke="#d1eeef" stroke-width="2"/><circle cx="207" cy="230" r="4" fill="#a3e0df"/><circle cx="222" cy="245" r="3" fill="#a3e0df"/></g>`;
  const bottles=`<g><path d="m302 168 55-11 32 15-55 12Z" fill="#f4fafa" stroke="#b4cdd6"/><path d="m302 168 32 16v93l-32-15Z" fill="#cde0e6"/><path d="m334 184 55-12v94l-55 11Z" fill="url(#${u}body)"/><path d="m314 118 35-7 24 11-35 8Z" fill="#0f8c97"/><path d="m314 118 24 12v38l-24-11Z" fill="#08717e"/><path d="m338 130 35-8v39l-35 7Z" fill="#0c8b97"/><path d="m342 208 32-7v29l-32 7Z" fill="#fff" stroke="#d7e5e9"/><path d="m349 215 18-4 M349 223l13-3" stroke="#7395a6" stroke-width="2"/><path d="m397 195 36-8 25 12-36 8Z" fill="#edf5fa" stroke="#bbcedb"/><path d="m397 195 25 12v57l-25-13Z" fill="#7fa7d1"/><path d="m422 207 36-8v58l-36 7Z" fill="url(#${u}blue)"/><path d="m401 183 30-6 20 10-30 7Z" fill="#f8fafb"/><path d="m401 183 20 11v12l-20-10Z" fill="#d5e2e9"/><path d="m421 194 30-7v12l-30 7Z" fill="#e8f0f4"/></g>`;
  const goggles=`<g transform="translate(88 267) rotate(-9)"><path d="M0 0c18-10 39-10 58-4l13 8 12-4c19-7 42-5 58 3l-5 34c-18 8-38 7-54-1l-11-13-12 10c-18 5-38 2-53-7Z" fill="#b8d9e1" stroke="#467d8f" stroke-width="3"/><path d="m10 5 43-2 9 13-9 12-36-3Z M82 11l12-7 35 4-3 22-31 1Z" fill="#f3fbfc" stroke="#75a8bb" stroke-width="2"/><path d="m19 10 22-1 M99 12l18 2" stroke="#fff" stroke-width="5" stroke-linecap="round"/><path d="m2 3-19 4-10 16 M138 9l20 10 4 19" fill="none" stroke="#2d6579" stroke-width="7" stroke-linecap="round"/></g>`;
  const notebook=`<g><path d="m248 282 75-15 62 30-76 16Z" fill="#3a728e"/><path d="m248 278 75-15 62 30-76 16Z" fill="#fcfdfd" stroke="#b6cdd7"/><path d="m260 280 23 12 M274 277l23 12 M288 274l23 12" stroke="#b6cdd7" stroke-width="2"/><path d="m315 274 28 14" stroke="#087f8c" stroke-width="3"/></g>`;
  const circuit=`<g><path d="m184 186 154-31 86 41-155 32Z" fill="#d5e7ec" stroke="#9fbfca" stroke-width="2"/><path d="m184 186 85 42v32l-85-42Z" fill="#7ea6b6"/><path d="m269 228 155-32v33l-155 31Z" fill="#aecbd7"/><path d="m212 194 78-15 44 21-79 16Z" fill="#087f8c"/><path d="m230 191 27-6 21 10-27 6Z" fill="#4ca8b0"/><path d="m296 210 48-10 M319 183l22-4 37 18-21 5" fill="none" stroke="#a7e1df" stroke-width="2"/><path d="M247 188v-58l57-12v50" fill="none" stroke="#e2ae50" stroke-width="6" stroke-linecap="round"/><path d="M340 190v-46l37-8v44" fill="none" stroke="#477ab6" stroke-width="6"/><path d="m265 117 31-6 21 10-31 7Z" fill="#eef7f8" stroke="#8fb5c1"/><path d="m265 117 21 11v28l-21-10Z" fill="#c8e0e4"/><path d="m286 128 31-7v28l-31 7Z" fill="#a4c6d0"/><circle cx="369" cy="211" r="6" fill="#3e7098"/><path d="m371 152 10-2" stroke="#fff" stroke-width="3"/></g>`;
  const ppe=`<g transform="translate(90 -8)"><path d="M110 239c-17-24-32-46-31-64 1-12 8-19 15-13l16 25-13-56c-2-12 11-16 16-4l14 41-4-66c0-13 14-14 16-1l5 62 8-58c2-12 15-9 14 3l-2 62 15-39c5-12 18-6 14 6l-10 58c-3 24-5 42-15 58l-5 28-60-1Z" fill="url(#${u}body)" stroke="#89b4c2" stroke-width="2"/><path d="m110 243 62 1-2 25-63-1Z" fill="#78b6c6"/><path d="M111 184c18-5 30 2 35 17 M128 237l7-34" stroke="#b0ccd7" stroke-width="2"/></g>`;
  let elements=bench+flask+bottles+goggles+notebook;
  if(kind==='chem')elements=bench+flask+bottles;
  if(kind==='electric')elements=bench+circuit+notebook;
  if(kind==='ppe')elements=bench+ppe+goggles;
  return `<svg class="lab-art" viewBox="0 0 580 380" fill="none" aria-hidden="true">${defs}${elements}</svg>`;
}

function shell(role,active,title,body,options={}){
  const student=role==='student',teacher=role==='teacher'||role==='collaborator',platform=role==='platform';
  const roleName=({student:'学生',teacher:'教师',collaborator:'教师',school:'学校管理员',college:'学院管理员',platform:'平台运维'})[role]||'学院管理员';
  const name=student?'林同学':platform?'平台运维员':role==='collaborator'?'许老师':teacher?'陈老师':'周管理员';
  const nav=student?[['book','我的课程','student-courses','courses'],['shield','安全学习','',''],['voice','学习助手','',''],['award','培训记录','','']]:teacher?[['book','课程与教学班','teacher-courses','courses']]:[['book','课程管理','admin-courses','courses'],['building',platform?'学校管理':role==='school'?'学院与专业':'专业管理',platform?'organizations-school':role==='school'?'organizations-college':'organizations-major','organizations'],['people','账号与授权','accounts','accounts'],['mail','学生账号邀请','invitations','invitations']];
  const scope=student?'化学学院 · 应用化学':teacher?'当前教学与显式课程授权':platform?'平台运维授权范围':role==='school'?'示范大学 · 全校':'示范大学 · 化学学院';
  return `<aside class="sidebar">${brand()}<div class="school-chip">${platform?'平台管理空间':'示范大学'}<span>${student?'学生学习空间':teacher?'教学协作空间':'管理空间'}</span></div><div class="nav-caption">${student?'我的学习':'常用工作'}</div><nav>${nav.map(([i,l,s,key])=>s?link(s,`${icon(i)}<span>${l}</span>`,`nav-item ${active===key?'active':''}`):`<div class="nav-item disabled">${icon(i)}<span>${l}</span><small>未开放</small></div>`).join('')}</nav><div class="sidebar-foot">${icon('shield')}<strong>让安全管理更智能</strong>让实验协同更畅通。</div></aside><div class="shell"><header class="topbar"><div class="crumbs">${icon('building','sm')}<span>${platform?'平台空间':'示范大学'}</span>${icon('chevron','sm')}<span class="current">${title}</span></div><div class="profile">${!student&&!platform?link('role-switch',`${icon('user','sm')}${roleName}${icon('down','sm')}`,'role-picker'):`<span class="role-picker">${roleName}</span>`}<span class="avatar">${name.slice(0,1)}</span><span class="profile-name">${name}<small>${student?'2026001001':platform?'运维账号':'当前身份已授权'}</small></span>${link('login',icon('logout','sm'),'muted')}</div></header><main class="workspace">${body}<div class="workspace-foot">${icon('shield','sm')}<span>${scope} · 仅显示当前身份可访问内容</span></div></main></div>${options.overlay||''}`;
}

function auth(password=false){
  const form=password?`<section class="password-card"><div class="auth-kicker">${icon('lock','sm')}保护你的账号</div><h2 class="mt16">设置新的登录密码</h2><p class="muted mt16">当前使用临时密码。修改后请使用新密码重新登录。</p><div class="password-rules"><div>${icon('check')}8–256 个字符</div><div>${icon('check')}建议使用不易猜测的密码</div><div>${icon('check')}与临时密码不同</div></div><div class="stack">${field('临时密码','Sample0000','','password')}${field('新密码','Sample000000','','password')}${field('确认新密码','Sample000000','','password')}</div>${btn('修改并重新登录','primary main-action','arrow','login')}<div class="auth-help">${link('login','退出当前账号','emphasis')}<span>修改后旧会话全部失效</span></div></section>`:`<section class="auth-card"><div class="auth-heading"><div class="auth-kicker">${icon('shield','sm')}实验室安全 · 教学协作</div><h2>欢迎使用安研通</h2><p>使用学校分配的账号，开启本次学习与协作。</p></div><form>${field('学校编码','DEMO','','input')}${field('账号','student.demo','账号与学号可能不同，请使用分配的账号。')}${field('密码','Sample000000','','password')}${btn('登录','primary main-action','arrow','student-courses')}</form><div class="auth-help"><span>账号或密码有误？请联系学校管理员</span>${link('service-settings',`${icon('settings','sm')}连接设置`,'row gap8 emphasis')}</div><div class="auth-note">${icon('lock','sm')}<div>账号由学校统一管理。首次登录需修改临时密码；请勿与他人共用账号。</div></div></section>`;
  return `<main class="auth"><section class="auth-visual">${brand()}<div class="auth-copy"><h1>每一次实验，<br>从安全与协作开始。</h1><p>连接学校、教师与学生，让课程归属清晰，<br>让实验室安全学习有序开展。</p></div><div class="auth-illustration">${labArt()}</div><div class="auth-footer"><strong>安研通——实验室安全智能协同管理平台</strong>让安全管理更智能，让实验协同更畅通。</div></section><section class="auth-main">${form}<div class="auth-bottom">安研通 · LabConnect</div></section></main>`;
}
function studentCourses(){
  const data=[['chem','','实验室基础安全','LAB-101','化学学院','陈老师'],['electric','blue','电气实验安全基础','ELE-102','工程学院','吴老师'],['ppe','sand','化学实验室操作规范','CHE-201','化学学院','许老师']];
  const cards=data.map(([art,tone,title,code,college,name])=>`<article class="course-tile"><div class="course-art ${tone}">${tag('课程已建立','gray')}${labArt(art)}</div><div class="course-body"><span class="mini-label muted">${college} · ${code}</span><h3>${title}</h3><div class="course-teacher"><span class="avatar">${name[0]}</span>${name}</div><div class="course-bottom"><span>学习内容待教师发布</span>${icon('lock','sm')}</div></div></article>`).join('');
  return shell('student','courses','我的课程',head('我的课程','查看已加入的课程与授课教师。',btn('刷新','','refresh'))+`<section class="course-intro"><div class="course-intro-copy"><div class="intro-subject">${icon('beaker','sm')}实验室安全学习</div><h2>先了解规范，再走进实验室。</h2><p>这里汇集你已加入的课程。教师发布学习内容后，<br>即可从对应课程开始学习。</p></div><div class="intro-art">${labArt('bench')}</div></section><section><div class="section-top"><div><h2>已加入的课程 <span class="muted">3</span></h2><p>课程信息由学校与授课教师维护</p></div><div class="course-search">${search('搜索课程名称、编码或教师')}</div></div><div class="course-list">${cards}</div></section>`);
}

function coursePage(admin=false,history=false){
  const index=`<aside class="catalog-index"><div class="index-heading">${history?'归档课程目录':'课程目录'} <span class="muted">${history?'1':'3'}</span></div><div class="index-tools">${search('搜索课程目录')}</div><div class="index-entry selected"><div class="row spread"><strong>实验室基础安全</strong>${tag(history?'已归档':'在用',history?'gray':'')}</div><p>LAB-101 · 化学学院</p><small>目录所有者：陈老师</small></div>${history?'':`<div class="index-entry"><strong>化学实验室操作规范</strong><p>CHE-201 · 化学学院</p><small>目录所有者：许老师</small></div><div class="index-entry"><strong>仪器使用安全</strong><p>LAB-203 · 化学学院</p><small>目录所有者：陈老师</small></div>`}<div class="index-note">课程目录保存共用的课程标识；每个教学班独立管理教师与学生名单。</div><div class="index-action">${btn('新建课程','soft','plus',admin?'new-course-admin':'new-course-teacher')}</div></aside>`;
  const rows=[['<strong>2026 级安全基础一班</strong><small>LAB-101-A · 化学学院</small>',person('陈老师','主讲教师'),tag('开放'),btn('管理班级','link','','class-overview')],['<strong>2026 级安全基础二班</strong><small>LAB-101-B · 化学学院</small>',person('许老师','主讲教师'),tag('开放'),btn('管理班级','link','',admin?'class-admin':'class-collaborator')],['<strong>2025 级安全基础班</strong><small>LAB-101-2025 · 化学学院</small>',person('陈老师','主讲教师'),tag('已归档','gray'),btn('查看历史','link','','class-archived')]];
  const visibleRows=history?rows.slice(2):rows.slice(0,2);
  const main=`<section class="paper"><div class="paper-header"><div><h2>实验室基础安全</h2><p>LAB-101 · 化学学院 · 目录所有者：陈老师</p></div>${btn('编辑目录','compact','edit','edit-catalog')}</div><div class="subtle-band">${icon('book','sm')}课程目录${tag(admin?'学院管理授权':'目录所有者','blue')}<span class="push muted">当前范围内 ${visibleRows.length} 个教学班</span></div><div class="toolbar filters">${search('搜索教学班名称或编码')}${`<div class="field"><label>状态</label><a class="control select" href="?screen=${history?'teacher-courses':'courses-history'}">${history?'已归档':'正在开课'}${icon('down','sm')}</a></div>`}${btn('搜索')}${(history?disabled('目录已归档'):btn('开设教学班','primary','plus','existing-catalog-new-class'))}</div>${table(['教学班','授课教师','状态','操作'],visibleRows)}${pagination(visibleRows.length)}<div class="section-note">${icon('info','sm')}查看课程目录不代表可以访问全部班级；班级名单按教师与管理员授权展示。</div></section>`;
  return shell(admin?'college':'teacher','courses',admin?'课程管理':'课程与教学班',head(admin?'课程管理':'课程与教学班',admin?'维护本学院课程目录，按授权管理教学班。':'先选课程目录，再进入教学班开展管理。',btn('刷新','','refresh'))+`<div class="split-index">${index}${main}</div>`);
}
function organizations(level='major'){
  const isSchool=level==='school',isCollege=level==='college',noun=isSchool?'学校':isCollege?'学院':'专业',role=isSchool?'platform':isCollege?'school':'college';
  const rows=(isSchool?[['示范大学','DEMO','学校'],['北辰示范学院','BC-DEMO','学校']]:isCollege?[['化学学院','CHEM','示范大学'],['工程学院','ENG','示范大学'],['生命科学学院','BIO','示范大学']]:[['应用化学','APPCHEM','化学学院'],['材料化学','MATCHEM','化学学院'],['化学工程与工艺','CHE-ENG','化学学院']]).map(([n,c,p],i)=>[`<strong>${n}</strong>`,c,p,tag(i===2?'已停用':'在用',i===2?'gray':''),btn('编辑','link','edit',isSchool?'organization-edit-school':isCollege?'organization-edit':'organization-edit-major')]);
  return shell(role,'organizations',`${noun}管理`,head(`${noun}管理`,isSchool?'平台层维护接入学校，学校之间数据独立。':isCollege?'维护本校组织结构，学院与专业各有清楚归属。':'仅维护已获授权学院内的专业。',btn(`新建${noun}`,'primary','plus',isSchool?'organization-new':isCollege?'organization-new-college':'organization-new-major'))+(isSchool?`<div class="tabs">${link('organizations-school','学校','active')}${link('organizations-college','学院')}${link('organizations-major','专业')}</div>`:isCollege?`<div class="tabs">${link('organizations-college','学院','active')}${link('organizations-major','专业')}</div>`:`<div class="tabs">${link('organizations-major','专业','active')}</div>`)+`<section class="paper"><div class="toolbar filters">${search(`搜索${noun}名称或编码`)}${!isSchool?field(isCollege?'学校':'学院',isCollege?'示范大学':'化学学院','','readonly'):''}${btn('搜索')}${btn('刷新','','refresh')}</div>${table([`${noun}名称`,'编码',isSchool?'所属层级':isCollege?'所属学校':'所属学院','状态','操作'],rows)}${pagination(rows.length)}<div class="section-note">${icon('shield','sm')}${isSchool?'学校管理员不会获得此平台级学校管理入口。':'所属学校由当前授权确定；跨学院访问仍需独立授权。'}</div></section>`);
}
function accounts(role='college'){
  const rows=[
    [person('林同学','student.demo'),'<span>2026001001</span><small>应用化学</small>','化学学院',tag('学生','blue'),tag('启用'),btn('编辑','link','','account-edit-student')+btn('重置密码','link','','account-reset')],
    [person('陈老师','teacher.chen'),'—','化学学院',`<div class="row-tags">${tag('教师','blue')}${tag('学院管理员')}</div>`,tag('启用'),role==='school'?btn('编辑','link','','account-edit-teacher'):'<span class="muted small-copy">当前身份仅可查看</span>'],
    [person('许老师','teacher.xu'),'—','化学学院',tag('教师','blue'),tag('启用'),btn('编辑','link','','account-edit-teacher')+btn('重置密码','link','','account-reset')],
    [person('周同学','student.zhou'),'<span>2025001028</span><small>材料化学</small>','化学学院',tag('学生','blue'),tag('停用','gray'),btn('编辑','link','','account-edit-student')+btn('重置密码','link','','account-reset')],
  ];
  return shell(role,'accounts','账号与授权',head('账号与授权',role==='school'?'维护本校账号，按管理员权限配置角色与学院范围。':'在本学院范围内维护账号、身份与访问授权。',btn('批量导入','','upload','csv-input')+btn('新建账号','primary','plus','account-new-student'))+`<section class="paper"><div class="toolbar filters">${search('搜索姓名、账号或学号')}${field('身份','全部身份','','select')}${field('学院范围','全部授权学院','','select')}${btn('搜索')}${btn('重置','link')}</div>${table(['姓名 / 登录账号','学号 / 专业','学院','身份','状态','操作'],rows)}${pagination(4)}<div class="section-note">${icon('lock','sm')}学生账号不能同时拥有教师或管理员身份；教师可按授权兼任管理员。</div></section>`);
}
function accountDrawer(teacher=false,existing=false){
  const title=existing?(teacher?'编辑教师账号':'编辑学生账号'):(teacher?'新建教职账号':'新建学生账号');
  const tabs=existing?`<div class="tabs drawer-tabs"><a class="active" href="?screen=${teacher?'account-edit-teacher':'account-edit-student'}">基本资料</a>${link('account-grant','角色授权')}${link('account-status','账号状态')}</div>`:'';
  const basic=`<section class="form-group"><h3>基本资料</h3><div class="form-grid">${field('学校','示范大学','','readonly')}${field('学院 *','化学学院','','select')}${field('登录账号 *',teacher?'teacher.chen':'student.demo',existing?'已建立的账号不可修改。':'登录标识独立于学号。',existing?'readonly':'input')}${field('姓名 *',teacher?'陈老师':'林同学')}${field(teacher?'学号（选填）':'学号 *',teacher?'':'2026001001',existing&&!teacher?'已建立的学生学号不能清空。':'与登录账号分别保存。')}${field(teacher?'专业（选填）':'专业 *',teacher?'未选择专业':'应用化学',existing&&!teacher?'已建立的学生专业不能清空。':'','select')}${field('性别（选填）','未填写','','select')}${field('联系方式（选填）','','用于校内必要联系。')}</div></section>`;
  const roles=!existing?`<section class="form-group"><h3>初始身份</h3><div class="role-grid"><div class="role-option ${!teacher?'selected':'disabled'}">${check('学生',!teacher,teacher)}</div><div class="role-option ${teacher?'selected':'disabled'}">${check('教师',teacher,!teacher)}</div><div class="role-option ${teacher?'selected':'disabled'}">${check('学院管理员',teacher,!teacher)}</div><div class="role-option disabled">${check('学校管理员',false,true)}</div></div><p class="section-note">${icon('info','sm')}${teacher?'教师可兼管理员；学院管理初始范围为所选学院。':'学生身份与教师、管理员身份互斥。'}</p></section>`:`<section class="form-group"><div class="row spread"><div><h3>当前身份</h3><div class="row">${tag(teacher?'教师':'学生','blue')}${teacher?tag('学院管理员'):''}</div></div>${btn('管理角色授权','link','','account-grant')}</div><div class="mt24">${btn('重置临时密码','danger','key','account-reset')}</div></section>`;
  const password=!existing?`<section class="form-group"><h3>首次登录</h3>${field('临时密码 *','Sample000000','8–256位；分配给本人后，首次登录必须修改。','password')}</section>`:'';
  return accounts(teacher?'school':'college')+drawer(title,existing?`${teacher?'陈老师 · teacher.chen':'林同学 · student.demo'} · 当前修订 3`:'资料、初始身份和临时密码在此一并设置。',tabs+basic+roles+password,btn('取消')+btn(existing?'保存账号资料':'创建账号','primary'));
}
function invitations(){
  const rows=[['化学学院 / 应用化学',tag('有效'),'1 / 30','2026-11-21 18:00',btn('撤销','link','','invite-issued')],['化学学院 / 材料化学',tag('有效'),'0 / 20','2026-11-18 18:00',btn('撤销','link','','invite-issued')],['化学学院 / 应用化学',tag('已撤销','gray'),'2 / 10','2026-10-30 18:00','<span class="muted">已失效</span>']];
  const form=`<section class="paper pad invite-form"><div><h2>创建学生账号邀请</h2><p class="muted mt16">为指定学院与专业设置注册范围。</p></div><div class="form-grid mt24">${field('学院 *','化学学院','','select')}${field('专业范围（选填）','应用化学','不限定时，学生选择学院内专业。','select')}${field('最多使用次数 *','30')}${field('有效期至 *','2026-11-21 18:00')}</div><div class="row spread mt24"><span class="muted small-copy">新凭据仅在创建成功时显示。</span>${btn('创建邀请','primary','plus','invite-issued')}</div></section>`;
  return shell('college','invitations','学生账号邀请',head('学生账号邀请','控制账号注册范围、有效期与使用次数。')+form+`<section class="paper mt24"><div class="paper-header"><div><h2>已创建的邀请</h2><p>列表仅显示邀请元信息</p></div>${btn('刷新','compact','refresh')}</div>${table(['注册归属','状态','已使用 / 上限','到期时间','操作'],rows)}${pagination(3)}</section>`);
}

function classPage(tab='overview',variant='primary'){
  const collaborator=variant==='collaborator',admin=variant==='admin',archived=variant==='archived';
  const role=admin?'college':collaborator?'collaborator':'teacher';
  const allowed=!collaborator&&!archived;
  const titles={overview:'班级概览',roster:'学生名单',requests:'申请审批',staff:'教师协作'};
  let content='';
  if(tab==='overview'){
    content=`<div class="content-columns">${paper('班级资料','课程与教学班分别维护',`<div class="paper-pad"><dl class="definition-grid"><div><dt>教学班名称</dt><dd>${archived?'2025 级安全基础班':'2026 级安全基础一班'}</dd></div><div><dt>教学班编码</dt><dd>${archived?'LAB-101-2025':'LAB-101-A'}</dd></div><div><dt>所属课程</dt><dd>实验室基础安全</dd></div><div><dt>开课学院</dt><dd>化学学院</dd></div><div><dt>主讲教师</dt><dd>陈老师</dd></div><div><dt>当前状态</dt><dd>${tag(archived?'已归档':'开放',archived?'gray':'')}</dd></div></dl></div>`,allowed?btn('编辑班级','compact','edit','class-edit'):'')}${paper('加入与退出','明确学生加入和退出的规则',`<div class="paper-pad"><div class="setting-line"><div><p>班级邀请码</p><small>${archived?'归档后停止加入':'由主讲教师生成并设置有效期'}</small></div>${tag(archived?'已关闭':'按需生成',archived?'gray':'blue')}</div><div class="setting-line"><div><p>加入需教师审批</p><small>通过后才出现在有效学生名单中</small></div>${allowed?toggle():tag('需要审批','gray')}</div><div class="setting-line"><div><p>退出需教师审批</p><small>保留退出记录与处理结果</small></div>${allowed?toggle():tag('需要审批','gray')}</div></div>`,allowed?btn('邀请码','compact','key','class-joincode'):'')}</div>${allowed?`<div class="danger-zone mt24"><div><h3>班级归属与生命周期</h3><p>转交主讲或归档前，请确认当前班级及操作影响。</p></div><div class="row">${btn('转交主讲','','people','class-transfer')}${btn('归档教学班','danger','archive','class-archive')}</div></div>`:''}`;
  }else if(tab==='roster'){
    const rows=[['林同学','student.demo','2026001001',tag('在班'),btn('移出','link')],['郑同学','student.zheng','2026001002',tag('在班'),btn('移出','link')],['何同学','student.he','2026001003',tag('在班'),btn('移出','link')],['周同学','student.zhou','2025001028',tag('已退出','gray'),btn('重新加入','link')]];
    content=`<section class="paper"><div class="toolbar">${search('搜索姓名、账号或学号')}${field('成员状态','全部状态','','select')}${btn('搜索')}${!archived?btn('批量导入','','upload','csv-roster')+btn('拉入学生','primary','plus','class-add-member'):''}</div>${table(['姓名','账号','学号','成员状态','操作'],rows)}${pagination(4)}<div class="section-note">${icon('info','sm')}移出、退出与审批结果保留记录，不删除学生账号。</div></section>`;
  }else if(tab==='requests'){
    const rows=[['孙同学',tag('申请加入','blue'),'2026-10-21 09:20',tag('待审批','amber'),btn('同意','link')+btn('拒绝','link')],['赵同学',tag('申请退出','gray'),'2026-10-21 08:45',tag('待审批','amber'),btn('同意','link')+btn('拒绝','link')],['钱同学',tag('申请加入','blue'),'2026-10-20 15:10',tag('已通过'),'<span class="muted">已处理</span>']];
    content=`<section class="paper"><div class="toolbar">${field('申请状态','全部状态','','select')}${btn('筛选')}${btn('刷新','','refresh')}</div>${table(['申请人','申请类型','申请时间','状态','操作'],rows)}${pagination(3)}<div class="section-note">${icon('shield','sm')}主讲教师与协作教师均可处理本班申请；相同申请重复处理时显示最新状态。</div></section>`;
  }else{
    const rows=[[person('陈老师','teacher.chen'),tag('主讲教师'),tag('有效'),'<span>班级设置、名单与审批、教师协作</span>','<span class="muted">通过转交变更主讲</span>'],[person('许老师','teacher.xu'),tag('协作教师','blue'),tag('有效'),'<span>学生名单与申请审批</span>',collaborator?'<span class="muted">主讲教师维护</span>':btn('移除协作','link')],[person('吴老师','teacher.wu'),tag('协作教师','blue'),tag('已移除','gray'),'<span>历史关系保留</span>',collaborator?'<span class="muted">主讲教师维护</span>':btn('恢复协作','link')]];
    content=`<section class="paper"><div class="paper-header"><div><h2>授课教师</h2><p>主讲教师负责关键设置，协作教师共同维护学生名单与审批。</p></div>${collaborator?'':btn('添加协作教师','primary','plus','class-add-staff')}</div>${table(['教师','授课身份','授权状态','可操作范围','操作'],rows)}${pagination(3)}</section>`;
  }
  return shell(role,'courses','教学班管理',`<div class="row mb24">${link('teacher-courses',`${icon('back','sm')}返回课程与教学班`,'row emphasis small-copy')}</div>${head(archived?'2025 级安全基础班':'2026 级安全基础一班',`实验室基础安全 · ${archived?'LAB-101-2025':'LAB-101-A'} · 化学学院`,tag(archived?'已归档':'开放',archived?'gray':'')+btn('刷新','','refresh'))}${archived?notice('此班级已归档。可查看历史资料，不能继续加入、审批或修改。','warn','archive'):collaborator?notice('你以协作教师身份进入，可管理学生名单与申请审批。关键设置与教师协作由主讲教师处理。'):admin?notice('当前使用化学学院管理授权。班级操作记录保留你的管理员身份。'):''}<div class="tabs class-tabs">${[['overview','班级概览','class-overview'],['roster','学生名单','class-roster'],['requests','申请审批','class-requests'],['staff','教师协作','class-staff']].map(([key,label,id])=>link(collaborator&&key==='staff'?'class-staff-readonly':id,label,tab===key?'active':'')).join('')}</div>${content}`);
}

function courseForm(kind='teacher'){
  const admin=kind==='admin',existing=kind==='existing';
  const body=`${existing?notice('本次仅在已有目录下开设教学班。指定其他教师主讲后，你不会自动获得该班名单访问权。','warn'):notice('同时建立同名、同代码的课程目录与首个教学班。后续可分别修改目录和班级名称。')}<div class="form-grid mt24">${field('开班学院 *','化学学院',admin?'学校管理员可按授权选择学院。':'按当前目录及授权范围选择。',admin?'select':'readonly')}${field('主讲教师 *',existing||admin?'许老师 · teacher.xu':'陈老师 · 当前教师',existing?'可指定同校其他教师。':admin?'从同校有效教师中选择。':'首个教学班由当前教师主讲。',existing||admin?'select':'readonly')}${field(existing?'教学班编码 *':'目录与首班编码 *',existing?'LAB-101-C':'LAB-101')}${field(existing?'教学班名称 *':'课程与首班名称 *',existing?'2026 级安全基础三班':'实验室基础安全')}</div>${existing||admin?`<div class="separator"></div><div class="row teacher-search">${field('查找可指定的本校教师','许老','至少输入2个字；只显示必要的候选资料。')}${btn('查找教师','','search')}</div>`:''}`;
  return coursePage(admin)+modal(existing?'开设教学班':'新建课程',existing?'课程目录：实验室基础安全 · LAB-101':'课程目录与教学班各自保留独立标识。',body,btn('取消')+btn(existing?'开设教学班':'创建课程与首班','primary'),'wide');
}
function csvPage(mode='preview'){
  const error=mode==='errors',uncertain=mode==='uncertain';
  const header=`<div class="csv-steps"><span>1 选择文件</span>${icon('chevron','sm')}<span class="${!uncertain?'current':''}">2 全量预检</span>${icon('chevron','sm')}<span class="${uncertain?'current':''}">3 确认导入</span></div><div class="row gap24 mb24">${field('导入内容','学生账号','','readonly')}${btn('下载 CSV 模板','','download')}</div><div class="csv-file"><span class="file-icon">${icon('file')}</span><div><strong>化学学院学生样例.csv</strong><small>3 行数据 · 1.2 KB · 文件上限 1 MiB / 500 行</small></div>${btn('重新选择','compact','','csv-preview')}</div>`;
  const rows=error?[[tag('第 2 行','red'),'student_no','必填学号为空','请补充学生学号'],[tag('第 3 行','red'),'major_id','专业不在当前学院范围','选择化学学院内有效专业']]:[['2','林同学','student.demo','2026001001','应用化学','••••••••'],['3','郑同学','student.zheng','2026001002','应用化学','••••••••'],['4','何同学','student.he','2026001003','应用化学','••••••••']];
  const tableBody=table(error?['CSV 行号','字段','问题','处理建议']:['CSV 行号','姓名','账号','学号','专业','临时密码'],rows);
  const status=uncertain?notice('连接中断，尚不能确认本次提交结果。请使用原请求重试，勿重新创建批次。','warn','wifi'):error?notice('发现 2 处错误，尚未写入任何账号。请修正文件并重新预检。','error','warning'):notice('全部 3 行预检通过。确认后一次提交；任意一行失败均不写入。','success','check');
  const retry=uncertain?`<div class="risk-block mt16"><strong>保留本次导入请求</strong><p>原文件与提交内容保持不变。重试会沿用原请求标识，避免重复创建账号；响应确认前保留此页面。</p></div>`:'';
  return accounts()+modal(uncertain?'确认本次导入结果':error?'修正 CSV 文件':'预览并确认导入','预检展示完整数据；临时密码始终遮蔽。',header+status+`<div class="paper mt16">${tableBody}</div>`+retry,btn('编辑 CSV','','edit','csv-input')+(error?disabled('确认导入'):btn(uncertain?'使用原请求重试':'确认导入 3 个账号','primary',uncertain?'refresh':'check',uncertain?'csv-uncertain':'')),'wide');
}
function accountGrants(){
  const body=`<div class="tabs drawer-tabs">${link('account-edit-teacher','基本资料')}<a class="active" href="?screen=account-grant">角色授权</a>${link('account-status','账号状态')}</div><section class="form-group"><h3>已有授权</h3><div class="grant-line"><div>教师<small>本校教学与课程授权</small></div>${btn('撤销授权','link')}</div><div class="grant-line"><div>学院管理员<small>化学学院</small></div>${btn('撤销授权','link')}</div><div class="mt16">${notice('撤销后，旧会话的后续请求立即按最新权限重新校验。')}</div></section><section class="form-group"><h3>新增授权</h3><div class="stack">${field('角色 *','学院管理员','','select')}${field('授权学院 *','化学学院','只能选择当前管理员可授权的学院。','select')}</div><div class="mt24">${btn('添加授权','primary','plus')}</div></section>`;
  return accounts('school')+drawer('管理角色授权','陈老师 · teacher.chen',body,btn('关闭'));
}
function newOrganization(level){
  const college=level==='college',label=college?'学院':'专业';
  return organizations(level)+modal(`新建${label}`,college?'当前身份：学校管理员':'当前身份：化学学院管理员',`<div class="form-grid">${field('所属学校 *','示范大学','','readonly')}${!college?field('所属学院 *','化学学院','','select'):''}${field(`${label}编码 *`,college?'CHEM-NEW':'CHEM-NEW','字母、数字、下划线或短横线。')}${field(`${label}名称 *`,college?'新示范学院':'新示范专业')}</div>`,btn('取消')+btn(`创建${label}`,'primary'));
}
function editOrganization(level){
  const school=level==='school',label=school?'学校':'专业';
  return organizations(level)+modal(`编辑${label}`,school?'平台管理空间 · DEMO':'示范大学 · 化学学院',`<div class="form-grid">${!school?field('所属学校','示范大学','','readonly')+field('所属学院','化学学院','','readonly'):''}${field(`${label}编码`,school?'DEMO':'APPCHEM','','readonly')}${field(`${label}名称 *`,school?'示范大学':'应用化学')}</div><div class="setting-line mt16"><div><p>启用${label}</p><small>${school?'停用后本校账号不能继续访问。':'停用保留历史资料，影响后续组织选择。'}</small></div>${toggle()}</div>`,btn('取消')+btn('保存修改','primary'));
}
function csvInput(roster=false){
  return (roster?classPage('roster'):accounts())+modal(roster?'批量加入学生':'批量开通账号',roster?'2026 级安全基础一班 · 不创建新学生账号':'示范大学 · 导入前请先下载对应模板',`<div class="csv-steps"><span class="current">1 准备内容</span>${icon('chevron','sm')}<span>2 全量预检</span>${icon('chevron','sm')}<span>3 确认导入</span></div><div class="row spread mb24"><span class="muted small-copy">UTF-8 CSV · 最多 500 行 · 文件上限 1 MiB</span>${btn('下载模板','','download')}</div><div class="csv-file"><span class="file-icon">${icon('upload')}</span><div><strong>${roster?'已选：班级名单样例.csv':'选择 UTF-8 CSV 文件'}</strong><small>也可以在下方直接编辑CSV内容</small></div>${btn('选择文件','compact')}</div>${field('CSV 内容',roster?'username\nstudent.demo\nstudent.zheng\nstudent.he':'在此粘贴或编辑CSV内容。\n账号模板需要为每位账号填写初始临时密码。','内容仅保留在当前页面内存；编辑后需重新预检。','area')}${roster?`<div class="mt16">${notice('仅将CSV中的已开通学生加入当前班级。预检全部通过后才能整批提交。')}</div>`:''}`,btn('取消')+btn('预检全部内容','primary','check',roster?'csv-roster':'csv-preview'),'wide');
}
function stateSheet(){
  const sample=(title,body)=>`<section class="state-specimen"><h3>${title}</h3>${body}</section>`;
  return shell('teacher','courses','状态规范草案',head('交互状态','设计规范参考页：集中展示组件状态，不作为新增业务页面。')+`<div class="state-grid">${sample('加载',`<div class="row muted"><span class="loader"></span>正在读取课程</div><div class="skeleton mt16"></div><div class="skeleton medium"></div><div class="skeleton short"></div>`)}${sample('空数据',`<div class="state-empty">${icon('book','lg')}<div><strong>当前范围内还没有课程</strong><p>可刷新，或联系授课教师核对名单。</p></div></div>`)}${sample('请求失败',notice('课程读取失败，请重试。','error','warning')+btn('重新加载','link','refresh'))}${sample('离线',notice('网络连接已断开。已显示信息可能不是最新状态。','warn','wifi')+`<p class="small-copy muted mt16">恢复网络后刷新；需要服务器确认的操作暂停。</p>`)}${sample('无权限',notice('当前身份没有此班级的访问权限。','warn','lock')+btn('返回可访问课程','link','back','teacher-courses'))}${sample('修订冲突',notice('内容已被其他管理员更新，请重新读取后再确认。','warn','refresh')+`<div class="row mt16">${btn('查看最新内容','compact')}${btn('保留输入并返回','compact')}</div>`)}${sample('尚未配置',notice('尚未配置服务地址。请先检查连接设置。','warn','settings')+btn('打开连接设置','link','settings','service-settings'))}${sample('未开放',`<div class="row"><span class="avatar">${icon('voice')}</span><div><strong>学习助手</strong><p class="small-copy muted">此功能尚未开放，开放后将在这里提供入口。</p></div>${tag('未开放','gray')}</div><div class="mt16">${disabled('进入学习助手')}</div>`)}</div>`);
}

function renderScreen(id){
  switch(id){
    case 'login':return auth();
    case 'login-error':return auth().replace('<form>',`<div class="mb24">${notice('学校、账号或密码不正确，请核对后重试。','error','warning')}</div><form>`);
    case 'first-password':return auth(true);
    case 'service-settings':return auth()+modal('服务连接设置','配置此设备访问安研通服务的地址。',`${field('服务地址 *','https://lab.example.edu.cn','示例地址。实际由学校管理员提供；保存后返回登录。')}${notice('修改服务地址后需要重新登录。请先核对学校及服务器来源。','', 'shield')}`,btn('取消')+btn('保存设置','primary'),'small');
    case 'student-courses':return studentCourses();
    case 'teacher-courses':return coursePage();
    case 'courses-history':return coursePage(false,true);
    case 'admin-courses':return coursePage(true);
    case 'organizations-school':return organizations('school');
    case 'organizations-college':return organizations('college');
    case 'organizations-major':return organizations('major');
    case 'accounts':return accounts();
    case 'account-new-student':return accountDrawer();
    case 'account-new-teacher':return accountDrawer(true);
    case 'account-edit-student':return accountDrawer(false,true);
    case 'account-edit-teacher':return accountDrawer(true,true);
    case 'account-grant':return accountGrants();
    case 'account-status':return accounts('school')+modal('停用此账号？','陈老师 · teacher.chen',`<div class="modal-warning-icon red">${icon('user')}</div><div class="risk-block"><strong>账号全部旧会话将被撤销</strong><p>本人将不能继续登录。若仍为在用教学班的主讲教师，请先完成班级交接。</p></div><p class="small-copy muted mt24">停用保留历史；可在账号管理中重新启用。</p>`,btn('取消')+btn('确认停用','danger'),'small');
    case 'account-reset':return accounts()+modal('重置林同学的密码','学生账号 student.demo · 2026001001',`<div class="modal-warning-icon red">${icon('key')}</div><div class="risk-block"><strong>当前全部会话将立即失效</strong><p>本人下次登录必须修改临时密码。此操作不会清除其课程和历史记录。</p></div><div class="mt24">${field('新临时密码 *','Sample000000','请通过学校约定渠道交给账号本人。','password')}</div>`,btn('取消')+btn('确认重置','danger'),'small');
    case 'invitations':return invitations();
    case 'invite-issued':return invitations()+modal('邀请已创建','化学学院 · 应用化学',`${notice('请现在妥善保存此凭据，关闭后列表不会再次显示明文。','success','check')}<div class="code-value mt24">DEMO-7K3P</div><div class="row spread mt16"><span class="muted small-copy">请只发给对应专业的学生</span>${btn('复制','compact','copy')}</div><div class="separator"></div><div class="summary-line"><span>使用上限</span><strong>30 次</strong></div><div class="summary-line"><span>到期时间</span><strong>2026-11-21 18:00</strong></div>`,btn('已保存，关闭','primary'),'small');
    case 'class-overview':return classPage();
    case 'class-roster':return classPage('roster');
    case 'class-requests':return classPage('requests','collaborator');
    case 'class-staff':return classPage('staff');
    case 'class-edit':return classPage()+modal('编辑班级设置','2026 级安全基础一班 · 当前修订 6',`${field('教学班名称 *','2026 级安全基础一班')}<div class="setting-line mt16"><div><p>加入本班需要审批</p><small>审核通过后进入有效学生名单。</small></div>${toggle()}</div><div class="setting-line"><div><p>退出本班需要审批</p><small>退出请求由授课教师处理。</small></div>${toggle()}</div>`,btn('取消')+btn('保存班级设置','primary'));
    case 'class-add-member':return classPage('roster')+modal('拉入已开通学生','2026 级安全基础一班',`${field('学生登录账号 *','student.demo','输入本校学生的准确登录账号。')}${notice('仅按准确账号拉入；不提供其他学院学生的完整账号目录。')}`,btn('取消')+btn('加入本班','primary'),'small');
    case 'class-add-staff':return classPage('staff')+modal('添加协作教师','2026 级安全基础一班',`<div class="row teacher-search">${field('查找本校教师','许老','至少2个字；按姓名或登录账号查找。')}${btn('查找','','search')}</div>${field('选择教师 *','许老师 · teacher.xu','候选信息仅用于当前班级协作。','select')}<div class="mt24">${notice('协作教师可调整本班学生名单和处理申请，不具有主讲的关键授权权限。')}</div>`,btn('取消')+btn('添加为协作教师','primary'));
    case 'class-collaborator':return classPage('overview','collaborator');
    case 'class-staff-readonly':return classPage('staff','collaborator');
    case 'class-admin':return classPage('overview','admin');
    case 'class-archived':return classPage('overview','archived');
    case 'class-joincode':return classPage()+modal('班级邀请码','2026 级安全基础一班 · 本次新生成',`<div class="code-value">DEMO-A6J9</div><div class="row spread mt16"><span class="muted small-copy">重置后旧加入码立即失效</span></div><div class="separator"></div>${field('新邀请码有效期至 *','2026-11-21 18:00','使用设备当前时区。')}<div class="mt16">${notice('重新生成会立即使旧邀请码失效。仅在本次成功生成后显示新码。','warn')}</div>`,btn('关闭')+btn('生成新邀请码','primary','refresh'));
    case 'class-transfer':return classPage()+modal('转交主讲教师','2026 级安全基础一班',`<div class="modal-warning-icon">${icon('people')}</div>${field('新主讲教师 *','许老师 · teacher.xu','只能选择本校有效教师。','select')}<div class="risk-block mt24"><strong>原主讲教师将失去本班当前授权</strong><p>转交给所选教师后返回可访问课程。历史关系与学生名单继续保留；管理员访问仍依照其授权范围。</p></div><div class="mt16">${check('我已核对班级与接任教师',false)}</div>`,btn('取消')+disabled('确认转交'));
    case 'class-archive':return classPage()+modal('归档此教学班？','2026 级安全基础一班 · LAB-101-A',`<div class="modal-warning-icon red">${icon('archive')}</div><div class="risk-block"><strong>归档后停止所有新增与修改操作</strong><p>关闭加入、名单变更和申请审批，保留班级资料与历史记录供查看。</p></div><div class="mt24">${field('输入教学班编码确认','LAB-101-A')}</div>`,btn('取消')+btn('确认归档','danger'),'small');
    case 'csv-input':return csvInput();
    case 'csv-input-roster':return csvInput(true);
    case 'csv-preview':return csvPage();
    case 'csv-roster':return classPage('roster')+modal('批量加入本班学生','2026 级安全基础一班 · 已开通学生',`${notice('全部 3 行通过预检；只更新当前班级名单，不重复创建账号。','success','check')}<div class="paper mt24">${table(['CSV 行号','已开通学生账号','操作'],[['2','student.demo',tag('加入本班')],['3','student.zheng',tag('加入本班')],['4','student.he',tag('加入本班')]])}</div><div class="section-note">${icon('info','sm')}修改内容后必须重新预检；失败不会部分写入。</div>`,btn('编辑 CSV','','edit','csv-input-roster')+btn('确认整批提交 3 行','primary'),'wide');
    case 'csv-errors':return csvPage('errors');
    case 'csv-uncertain':return csvPage('uncertain');
    case 'new-course-teacher':return courseForm();
    case 'new-course-admin':return courseForm('admin');
    case 'existing-catalog-new-class':return courseForm('existing');
    case 'edit-catalog':return coursePage(true)+modal('编辑课程目录','实验室基础安全 · 当前修订 4',`<div class="form-grid">${field('课程编码','LAB-101','','readonly')}${field('所属学院','化学学院','','readonly')}${field('课程名称 *','实验室基础安全','','input','full')}${field('目录状态','使用中（可切换归档）','','select','full')}${field('目录所有者 *','陈老师 · teacher.chen','变更所有者不自动转交已有教学班。','select','full')}</div><div class="risk-block mt24"><strong>目录状态变更</strong><p>存在活动教学班时不能归档目录。已归档目录可恢复使用，历史不会删除。</p></div>`,btn('取消')+btn('保存修改','primary'));
    case 'organization-edit':return organizations('college')+modal('编辑学院','示范大学 · CHEM',`<div class="form-grid">${field('所属学校','示范大学','','readonly')}${field('学院编码','CHEM','','readonly')}${field('学院名称 *','化学学院','','input','full')}</div><div class="setting-line mt16"><div><p>启用学院</p><small>停用会影响相关账号、课程及访问范围。</small></div>${toggle()}</div>${notice('所属学校不在此变更。停用前应核对受影响组织与使用中的账号。','warn')}`,btn('取消')+btn('保存修改','primary'));
    case 'organization-new':return organizations('school')+modal('新建学校','当前身份：平台运维',`<div class="stack">${field('学校编码 *','DEMO-NEW','用于账号登录时识别学校。')}${field('学校名称 *','新示范大学')}<p class="muted small-copy">创建后启用；后续可在组织编辑中停用。</p></div>`,btn('取消')+btn('创建学校','primary'));
    case 'organization-new-college':return newOrganization('college');
    case 'organization-new-major':return newOrganization('major');
    case 'organization-edit-school':return editOrganization('school');
    case 'organization-edit-major':return editOrganization('major');
    case 'role-switch':return coursePage()+`<section class="popover"><div class="popover-title">陈老师的已授权身份</div><div class="popover-item selected">${icon('book')}<div>教师<small>本人教学及课程授权</small></div>${icon('check')}</div><div class="popover-item">${icon('building')}<div>学院管理员<small>仅化学学院</small></div></div><div class="popover-footer">切换后按该身份重新读取数据与可操作范围。</div></section>`;
    case 'states-sheet':return stateSheet();
    default:return `<main class="empty"><h1>未找到设计页面</h1>${link('login','返回登录稿')}</main>`;
  }
}
if(typeof module!=='undefined')module.exports={VERSION,SCREENS};
if(typeof document!=='undefined'){
  const requested=new URLSearchParams(location.search).get('screen')||'login';
  const meta=SCREENS.find(s=>s.id===requested);
  document.title=`${meta?meta.title:'设计稿'} · 安研通 · ${VERSION}`;
  document.getElementById('app').innerHTML=renderScreen(requested);
  document.addEventListener('submit',event=>event.preventDefault());
  document.documentElement.dataset.designVersion=VERSION;
  document.documentElement.dataset.screen=requested;
}
