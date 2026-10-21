'use strict';
// Design-only simulation. No product imports, storage, permission, audio or API calls.
const VERSION='UI-ASSISTANT-2026.10-v1';
const PALETTES=[['white','经典白','#FFFFFF'],['teal','青绿','#087F8C'],['blue','蓝色','#2563EB'],['charcoal','炭灰','#30363F']];
const SCREENS=[
 ['web-capsule','胶囊入口','网页',1440,960,'capsule','chat'],
 ['web-dialog','展开对话','网页',1440,960,'panel','chat'],
 ['web-history','最近对话','网页',1440,960,'panel','history'],
 ['web-dock-left','左侧半隐藏','网页',1440,960,'left','chat'],
 ['web-dock-right','右侧半隐藏','网页',1440,960,'right','chat'],
 ['web-settings','个人助手设置','网页',1440,960,'settings','chat'],
 ['web-disabled','关闭后的设置入口','网页',1440,960,'disabled','chat'],
 ['web-recording','录音与停止','网页',1440,960,'panel','recording'],
 ['web-transcript','确认识别文字','网页',1440,960,'panel','transcript'],
 ['web-generating','文字生成中','网页',1440,960,'panel','generating'],
 ['web-complete','收起后的完成提示','网页',1440,960,'capsule','complete'],
 ['web-exam','正式考试暂停','网页',1440,960,'panel','exam'],
 ['web-unknown','考试状态待核实','网页',1440,960,'panel','unknown'],
 ['web-unconfigured','学校尚未配置','网页',1440,960,'panel','unconfigured'],
 ['web-offline','服务连接失败','网页',1440,960,'panel','offline'],
 ['web-mic-denied','麦克风权限未开启','网页',1440,960,'panel','microphone'],
 ['web-context','选择授权教学班','网页',1440,960,'panel','context'],
 ['web-new','新对话继承当前班','网页',1440,960,'panel','empty'],
 ['web-delete','删除对话确认','网页',1440,960,'panel','delete'],
 ['web-clear','清空全部历史确认','网页',1440,960,'panel','clear'],
 ['windows-dialog','Windows应用内悬浮','Windows',1280,900,'panel','chat'],
 ['windows-compact','Windows小窗口','Windows',900,700,'panel','chat'],
 ['windows-scale-125','Windows缩放125%参考','Windows',1024,720,'panel','chat',1.25],
 ['windows-scale-150','Windows缩放150%参考','Windows',852,600,'panel','chat',1.5],
 ['mobile-capsule','手机胶囊','Android',390,844,'capsule','chat'],
 ['mobile-small','可移动小窗','Android',390,844,'panel','chat'],
 ['mobile-full','完整对话','Android',390,844,'full','chat'],
 ['mobile-history','手机最近对话','Android',390,844,'full','history'],
 ['mobile-clear','手机清空历史确认','Android',390,844,'full','clear'],
 ['mobile-new','手机新对话','Android',390,844,'full','empty'],
 ['mobile-keyboard','输入与键盘避让','Android',390,844,'full','keyboard'],
 ['mobile-dock-left','手机左侧半隐藏','Android',390,844,'left','chat'],
 ['mobile-dock-right','手机右侧半隐藏','Android',390,844,'right','chat'],
 ['mobile-settings','手机助手设置','Android',390,844,'settings','chat'],
 ['mobile-disabled','手机关闭后可恢复','Android',390,844,'disabled','chat'],
 ['mobile-recording','手机录音','Android',390,844,'full','recording'],
 ['mobile-transcript','手机识别文字确认','Android',390,844,'full','transcript'],
 ['mobile-exam','手机考试暂停','Android',390,844,'full','exam'],
 ['mobile-unconfigured','手机尚未配置','Android',390,844,'full','unconfigured'],
 ['mobile-offline','手机连接失败','Android',390,844,'full','offline'],
 ['mobile-mic-denied','手机麦克风权限','Android',390,844,'full','microphone'],
 ['mobile-360-small','360px小窗','Android',360,780,'panel','chat'],
 ['mobile-360-full','360px全屏','Android',360,780,'full','chat'],
 ['mobile-360-keyboard','360px输入避让','Android',360,780,'full','keyboard'],
 ...PALETTES.map(([id,name])=>[`theme-${id}`,`${name}外壳对照`,'配色',980,760,'theme','chat',1,id]),
].map(([id,title,platform,width,height,view,content,dpr=1,theme='white'])=>({id,title,platform,width,height,view,content,dpr,theme,version:VERSION,synthetic_data:true}));
const PATHS={
 edit:'M14.5 4.5 19.5 9.5 M13 6l5 5 M16.5 2.5l5 5L10 19l-7 2 2-7L16.5 2.5Z',
 wave:'M3 10v4 M7 6v12 M12 3v18 M17 7v10 M21 10v4',
 history:'M3 11a9 9 0 1 1 2.6 7 M3 4v7h7 M12 7v5l3 2',
 minus:'M5 12h14',expand:'M8 3H3v5 M16 3h5v5 M3 16v5h5 M21 16v5h-5',
 shrink:'M3 8h5V3 M21 8h-5V3 M8 21v-5H3 M16 21v-5h5',
 close:'m6 6 12 12 M18 6 6 18',book:'M3 4h7l2 2 2-2h7v16h-7l-2 2-2-2H3V4Z M12 6v16',
 down:'m7 10 5 5 5-5',back:'m14 5-7 7 7 7',right:'m9 5 7 7-7 7',
 mic:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5Z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8',
 send:'m12 5 0 14 M6 11l6-6 6 6',play:'m8 4 12 8-12 8V4Z',stop:'M6 6h12v12H6V6Z',
 copy:'M8 8h13v13H8V8Z M5 16H3V3h13v2',check:'m5 12 4 4L19 6',
 lock:'M5 10h14v12H5V10Z M8 10V6a4 4 0 0 1 8 0v4',
 wifi:'M3 8a15 15 0 0 1 18 0 M6 12a10 10 0 0 1 12 0 M9 16a5 5 0 0 1 6 0 M12 20h.01',
 refresh:'M4 11a8 8 0 0 1 13-6l3 3 M20 3v5h-5 M20 13a8 8 0 0 1-13 6l-3-3 M4 21v-5h5',
 settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3Z',
 trash:'M3 6h18 M9 6V3h6v3 M6 6l1 15h10l1-15 M10 10v7 M14 10v7',
 battery:'M2 7h18v10H2V7Z M22 10v4 M5 10h10v4H5V10Z',signal:'M4 19v-3 M9 19v-7 M14 19V8 M19 19V4',
 cloud:'M7 18H5a4 4 0 1 1 1-7.9 6 6 0 0 1 11.6-1.5A5 5 0 0 1 19 18h-2 M12 13v8 m-3-3 3 3 3-3',
 plus:'M12 5v14 M5 12h14',more:'M5 12h.01 M12 12h.01 M19 12h.01',
};
const icon=n=>`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${PATHS[n]||PATHS.more}"/></svg>`;
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const ib=(action,name,label,extra='')=>`<button class="icon-button ${extra}" type="button" data-action="${action}" aria-label="${label}" title="${label}">${icon(name)}</button>`;
const button=(action,label,style='',name='')=>`<button class="button-label ${style}" type="button" data-action="${action}">${name?icon(name):''}${label}</button>`;
const contextBar=(short=false)=>`<div class="context-bar">${icon('book')}<span class="context-text" title="${state?.contextChosen?'2026级安全基础一班':'尚未选择教学班'}">${!state?.contextChosen?'选择本次对话的教学班':short?'安全基础一班':'2026级安全基础一班'}</span><span class="context-mark">${state?.contextChosen?'本班资料':'待选择'}</span></div>`;
const question='个人防护主要看哪些内容？';
const response=`<p>这份示例课件将个人防护分成三项：<strong>穿着要求、防护用品和离开前的检查</strong>。</p><p>你可以先阅读对应章节，再结合本次实验的教师要求学习。</p>`;
const history=[['个人防护主要看哪些内容？','安全基础一班','14:32'],['怎样查看课件中的引用？','安全基础一班','10:08'],['复习试剂标签的阅读要点','化学实验安全二班','昨天'],['实验前需要准备哪些学习材料？','安全基础一班','10月20日']];
let active, state;
function capsule(extra=''){
 return `<div class="capsule ${extra}" data-drag="capsule" aria-label="可拖动的学习助手"><span class="capsule-drag" aria-hidden="true"></span><button type="button" data-action="open" aria-label="打开文字对话" title="打开文字对话">${icon('edit')}</button><span class="divider"></span><button type="button" data-action="voice" aria-label="打开语音操作" title="打开语音操作">${icon('wave')}</button>${state?.complete?'<i class="complete-dot" aria-label="有新回答"></i>':''}</div>`;
}
function dock(side){return `<div class="dock ${side}" data-drag="dock"><button type="button" data-action="restore" aria-label="恢复学习助手"><span class="dock-dot"></span></button></div>`;}
function chat(){return `<div class="message-user">${question}</div><article class="answer">${response}<button type="button" class="citation" data-action="citation">${icon('book')}<span>实验室安全基础<small> · 示例资料</small><br><small>版本 1 · 第 4–6 页</small></span>${icon('right')}</button><div class="answer-actions">${ib('play','play','播放这条回答')}${ib('copy','copy','复制回答')}<span>依据本班已发布资料</span></div></article>`;}
function historyBody(){if(state.emptyHistory)return `<div class="state-area"><div class="state-symbol">${icon('history')}</div><h2>还没有对话</h2><p>从一门已加入的课开始，提问记录会保留在这里。</p><div class="flow-actions">${button('new','新建对话','primary')}</div></div>`;return `<p class="history-group">今天</p>${history.map(([title,scope,time],i)=>`${i===2?'<p class="history-group">更早</p>':''}<button type="button" class="history-entry ${i===0?'current':''}" data-action="select-history" data-index="${i}"><span><strong>${title}</strong><small>${scope} · ${time}</small></span>${icon('right')}</button>`).join('')}`;}
const STATES={
 exam:['lock','正式考试期间，助手已暂停','考试结束后将重新核实可用状态。此时不会显示历史对话、收音或播报。','查看考试状态','verify','warn'],
 unknown:['lock','暂时无法核实考试状态','为避免考试期间继续辅导，助手和历史暂不可用。连接恢复后请重新核实。','重新核实','verify','warn'],
 unconfigured:['settings','本校尚未开启 AI 助手','学校管理员完成配置后即可使用。你仍可正常访问课程及学习资料。','返回课程','collapse',''],
 offline:['wifi','暂时连不上服务','请检查网络后重试。已经输入的文字仍保留在这里。','重试连接','retry',''],
 microphone:['mic','还不能使用麦克风','请在系统或浏览器设置中允许录音。你也可以继续输入文字。','改用文字','chat',''],
};
function stateBody(type){const [symbol,title,copy,label,action,color]=STATES[type];return `<div class="state-area"><div class="state-symbol ${color}">${icon(symbol)}</div><h2>${title}</h2><p>${copy}</p><div class="flow-actions">${button(action,label,'primary')}${type==='microphone'?button('mic-help','如何开启'):''}</div>${type==='exam'?'<p class="small-note">暂停范围：此学生账号的全部平台 AI 辅导</p>':''}</div>`;}
function recording(){return `<div class="recording"><h2>正在听你说</h2><p>说完后停止录音，再确认识别文字。</p><div class="voice-wave" aria-hidden="true">${[15,25,40,56,33,67,49,73,42,60,30,45,22,37,16].map((h,i)=>`<i class="wave-${i}"></i>`).join('')}</div><div class="voice-timer"><span class="recording-dot"></span>00:08</div><div class="recording-controls"><button class="text-action" type="button" data-action="cancel-record">取消</button><button class="record-stop" type="button" data-action="stop-record" aria-label="停止录音并识别">${icon('stop')}</button><span class="small-note">停止</span></div></div>`;}
function transcript(){return `<p class="transcript-label">录音已停止</p><h2 class="transcript-title">确认一下你想问的内容</h2><textarea class="transcript-input" aria-label="修改识别文字">${state.draft||question}</textarea><p class="transcript-note">可以修改文字，确认后才会发送给助手。</p><button class="text-action" type="button" data-action="voice">重新录音</button>`;}
function scopeBody(){return `<div class="state-symbol">${icon('book')}</div><h2 class="transcript-title">这次想问哪门课？</h2><p class="small-note">选择后，本次对话只使用该班有权访问的资料。</p>${[['安全基础一班','实验室基础安全 · 2026级'],['化学实验安全二班','化学实验安全 · 2026级']].map(([name,desc])=>`<button class="scope-choice" type="button" data-action="choose-context"><strong>${name}</strong><small>${desc}</small></button>`).join('')}`;}
function deleteBody(){const all=state.content==='clear';return `<div class="confirm-area"><div class="state-symbol warn">${icon('trash')}</div><h2>${all?'清空全部对话？':'删除这段对话？'}</h2><p>删除后，三端都不能继续查看${all?'这些聊天':'这段聊天'}。正式学习成绩不受影响。</p><div class="confirm-card"><strong>${all?'当前账号的全部文字对话':question}</strong><small>${all?'包含不同教学班的本人对话':'安全基础一班 · 今天'}</small></div><div class="flow-actions">${button('history','取消')}${button(all?'confirm-clear':'confirm-delete',all?'确认清空':'确认删除','danger')}</div></div>`;}
function composer(){
 if(['exam','unknown','unconfigured'].includes(state.content))return `<footer class="composer-disabled">${icon('lock')}<span>${state.content==='unconfigured'?'配置完成后可提问':'辅导暂停，历史内容暂不可见'}</span></footer>`;
 if(state.content==='recording')return '<footer class="voice-foot">收起或切到后台会停止录音。<br>录音仅用于本次识别，处理后默认删除。</footer>';
 if(state.content==='transcript')return `<footer class="transcript-footer">${button('cancel-record','取消')}${button('send-voice','确认并发送','primary','send')}</footer>`;
 if(state.content==='history')return `<footer class="history-foot"><p class="small-note">保留至手动删除</p><div><button class="text-action" type="button" data-action="delete">删除当前对话</button><button class="text-action" type="button" data-action="clear">清空全部</button></div></footer>`;
 if(['delete','clear','context'].includes(state.content))return '';
 return `<footer class="composer"><div class="input-box"><textarea aria-label="输入问题" placeholder="继续问点什么…">${state.content==='keyboard'?'怎么找到对应的课件章节？':state.draft||''}</textarea><div class="input-tools"><span>当前对话：安全基础一班</span><div>${ib('voice','mic','打开语音操作')}${ib(state.content==='generating'?'stop-generation':'send',state.content==='generating'?'stop':'send',state.content==='generating'?'停止生成':'发送问题','send-button')}</div></div></div><div class="compact-composer"><button class="expand-input" type="button" data-action="input">点此提问…</button>${ib('voice','mic','展开语音操作')}</div></footer>`;
}
function panel(){
 const mini=state.mobile&&state.view!=='full';
 const heading=state.content==='history'?'最近对话':['delete','clear'].includes(state.content)?'管理对话':'学习助手';
 const gated=['exam','unknown','unconfigured'].includes(state.content);
 let tools=gated?(state.mobile&&state.view==='full'?ib('shrink','shrink','收回小窗'):'')+(mini?ib('expand','expand','展开为全屏'):'')+ib('collapse','minus','收起助手'):mini?ib('expand','expand','展开为全屏')+ib('collapse','minus','收起助手'):['history','delete','clear'].includes(state.content)?ib('chat','back','返回当前对话')+ib('new','edit','新建对话')+ib('collapse','minus','收起助手'):ib('history','history','查看最近对话')+ib('new','edit','新建对话')+(state.mobile?ib('shrink','shrink','收回小窗'):'')+ib('collapse','minus','收起助手');
 let body=STATES[state.content]?stateBody(state.content):state.content==='empty'?`<div class="state-area"><div class="state-symbol">${icon('edit')}</div><h2>从这门课开始提问</h2><p>当前范围：安全基础一班。<br>可以输入问题，也可以使用语音。</p></div>`:state.content==='history'?historyBody():state.content==='recording'?recording():state.content==='transcript'?transcript():state.content==='context'?scopeBody():['delete','clear'].includes(state.content)?deleteBody():state.content==='generating'?`<div class="message-user">${question}</div><div class="status-inline"><span class="typing-dots"><i></i><i></i><i></i></span><span>正在查阅本班资料</span></div><p class="generating-text">收起后，文字回答仍可继续。</p><button class="stop-answer" type="button" data-action="stop-generation">${icon('stop')}停止生成</button>`:chat();
 return `<section class="assistant-panel ${state.view==='full'?'fullscreen':''} ${state.content==='keyboard'?'key-view':''}" aria-label="学习助手" data-view="${state.view}" data-content="${state.content}"><header class="assistant-header" data-drag="panel"><div class="header-name">${heading}${!state.mobile?'<small>安研通</small>':''}</div>${tools}</header><div class="assistant-inner">${contextBar(mini)}<div class="conversation ${state.content==='transcript'?'transcript-body':''}">${body}</div>${composer()}</div></section>`;
}
function settings(){return `<div class="settings-mask"><section class="settings-card" role="dialog" aria-modal="true" aria-label="个人助手设置"><header class="settings-header"><div><h1>个人助手设置</h1><p>林同学 · 当前设备</p></div>${ib('close-settings','close','关闭个人设置')}</header><div class="settings-body"><div class="setting-line"><div><strong>显示悬浮助手</strong><p>在安研通内随时提问。关闭后，对话历史仍保留。</p></div><div class="switch-wrap"><button class="switch ${!state.enabled?'off':''}" type="button" role="switch" aria-label="显示悬浮助手" aria-checked="${state.enabled}" data-action="toggle-enabled"></button></div></div>${!state.enabled?'<div class="off-callout"><strong>悬浮助手已关闭</strong>当前设备停止收音、播报，并取消未完成请求。需要时可在这里重新开启。</div>':''}<h2 class="palette-title">助手配色</h2><p class="palette-copy">更换胶囊和外壳颜色，聊天内容保持浅色。</p><div class="swatches">${PALETTES.map(([id,name])=>`<button class="swatch" type="button" data-action="theme" data-theme="${id}" aria-label="${name}配色" aria-pressed="${state.theme===id}"><span class="swatch-color theme-${id}">${state.theme===id?icon('check'):''}</span><span class="swatch-name">${name}</span></button>`).join('')}</div><div class="setting-line"><div><strong>语音回答自动播报</strong><p>文字提问保持安静，语音提问的回答自动朗读。</p></div><div class="switch-wrap"><button class="switch ${!state.autoSpeak?'off':''}" type="button" role="switch" aria-label="语音回答自动播报" aria-checked="${state.autoSpeak}" data-action="toggle-speak"></button></div></div><p class="small-note">${icon('lock')}这些偏好仅用于当前服务、学校、账号和设备。</p></div><footer class="settings-footer"><p>设置关闭后，可从<br>账号菜单再次进入。</p>${button('close-settings','完成','primary')}</footer></section></div>`;}
function keyboard(){return `<div class="keyboard" aria-label="软键盘布局模拟"><div class="keyboard-suggestions"><span>怎么</span><span>找到</span><span>课件</span></div>${['qwertyuiop','asdfghjkl','zxcvbnm'].map((row,i)=>`<div class="keyboard-row">${i===2?'<span class="wide-key">⇧</span>':''}${row.split('').map(k=>`<span>${k}</span>`).join('')}${i===2?'<span class="wide-key">⌫</span>':''}</div>`).join('')}<div class="keyboard-row"><span class="wide-key">?123</span><span class="wide-key">中/英</span><span class="space-key">空格</span><span class="enter-key">完成</span></div></div>`;}
function applyPosition(){
 const el=document.querySelector('.assistant-panel,.capsule,.dock');if(!el)return;
 if(state.position&&state.view!=='full'&&!['left','right','theme'].includes(state.view)){
  const surface=document.querySelector('.surface').getBoundingClientRect();
  const box=el.getBoundingClientRect();
  el.style.left=Math.max(8,Math.min(state.position.x,surface.width-box.width-8))+'px';
  el.style.top=Math.max(8,Math.min(state.position.y,surface.height-box.height-8))+'px';el.style.right='auto';el.style.bottom='auto';
 }
 document.querySelectorAll('.voice-wave i').forEach((el,i)=>el.style.height=[15,25,40,56,33,67,49,73,42,60,30,45,22,37,16][i]+'px');
}
function draw(){
 document.body.className=`platform-${active.platform==='Windows'?'windows':active.platform==='Android'?'android':'web'} ${state.mobile?'mobile':''} theme-${state.theme} ${state.content==='keyboard'?'has-keyboard':''}`;
 const chrome=active.platform==='Windows'?`<div class="windows-bar"><span class="app-symbol">安</span>安研通<span class="windows-controls"><span>${icon('minus')}</span><span>${icon('expand')}</span><span>${icon('close')}</span></span></div>`:active.platform==='Android'?`<div class="android-status"><span>14:32</span><span>${icon('signal')}${icon('wifi')}${icon('battery')}</span></div><div class="android-gesture"></div>`:'';
 if(state.view==='theme'){
  const entry=PALETTES.find(x=>x[0]===state.theme);
  document.getElementById('scene').innerHTML=`<div class="theme-stage theme-${state.theme}"><div class="theme-heading"><p>安研通 · 悬浮助手</p><h1>${entry[1]}</h1><small>同一种外壳，两种尺寸。</small></div>${capsule()}${panel()}<div class="theme-caption"><div class="theme-color-chip"><i></i><strong>${entry[1]}</strong><code>${entry[2]}</code></div><p>配色用于胶囊、标题栏与外框。<br>聊天正文始终清楚、安静。</p></div></div>`;
  applyPosition();bind();return;
 }
 const bg=state.mobile?'../mobile.html?screen=student-courses':'../prototype.html?screen=student-courses';
 const floating=['settings','disabled','hidden'].includes(state.view)?'':state.view==='capsule'?capsule()+(state.complete?`<div class="completion-note">${icon('check')}回答已准备好</div>`:''):['left','right'].includes(state.view)?dock(state.view):panel();
 document.getElementById('scene').innerHTML=`${chrome}<main class="surface"><iframe class="background" title="已批准UI-v1的静态课程背景" tabindex="-1" aria-hidden="true" src="${bg}"></iframe><button class="account-settings-hit" type="button" data-action="open-settings" aria-label="从账号菜单打开个人助手设置"></button>${floating}${['settings','disabled'].includes(state.view)?settings():''}</main>${state.content==='keyboard'?keyboard():''}`;
 document.documentElement.dataset.designVersion=VERSION;document.documentElement.dataset.designScreen=active.id;
 const background=document.querySelector('.background');
 const updateNavigation=()=>{for(const entry of background?.contentDocument?.querySelectorAll('.nav-item,.mobile-bottom-item')||[]){if(!entry.textContent.includes('学习助手'))continue;for(const small of entry.querySelectorAll('small'))if(small.textContent.includes('未开放'))small.remove();entry.classList.remove('disabled');entry.removeAttribute('aria-disabled');entry.setAttribute('title','唤起同一悬浮助手（设计示例）');}};
 background?.addEventListener('load',updateNavigation);if(background?.contentDocument?.readyState==='complete')updateNavigation();
 applyPosition();bind();
}
function preserveDraft(){const input=document.querySelector('.input-box textarea,.transcript-input');if(input)state.draft=input.value;}
function toast(text){document.querySelector('.demo-toast')?.remove();const el=document.createElement('div');el.className='demo-toast';el.role='status';el.textContent=text;document.querySelector('#scene').append(el);setTimeout(()=>el.remove(),2200);}
function action(name,el){
 if(Date.now()<state.suppressUntil)return;preserveDraft();
 if(['exam','unknown','unconfigured'].includes(state.content)&&['voice','history','new','chat','send','send-voice','select-history','choose-context','delete','clear','play'].includes(name)){state.view=state.mobile?'full':'panel';draw();return;}
 if(name==='theme'){state.theme=el.dataset.theme;draw();return;}
 if(name==='open'||name==='restore'){state.view=state.previousView==='full'?'full':'panel';state.complete=false;draw();return;}
 if(name==='collapse'){state.previousView=state.view;state.view='capsule';state.playing=false;if(state.content==='recording')state.content='chat';state.position=null;draw();return;}
 if(name==='expand'||name==='input'){state.view='full';draw();if(name==='input')document.querySelector('.input-box textarea')?.focus();return;}
 if(name==='shrink'){state.view='panel';state.position=null;draw();return;}
 if(name==='voice'){state.view=state.mobile?'full':'panel';state.content='recording';state.playing=false;draw();return;}
 if(name==='stop-record'){state.content='transcript';state.draft=question;draw();return;}
 if(name==='cancel-record'||name==='chat'){state.content='chat';state.playing=false;draw();return;}
 if(name==='history'){state.content='history';state.view=state.mobile?'full':'panel';draw();return;}
 if(name==='new'){state.content=state.contextChosen?'empty':'context';state.view=state.mobile?'full':'panel';state.draft='';draw();return;}
 if(name==='choose-context'){state.contextChosen=true;state.content='empty';state.draft='';draw();return;}
 if(name==='select-history'){state.contextChosen=true;state.content='chat';state.draft='';draw();return;}
 if(name==='delete'){state.content='delete';draw();return;}
 if(name==='clear'){state.content='clear';draw();return;}
 if(name==='confirm-clear'){state.emptyHistory=true;state.content='history';draw();return;}
 if(name==='confirm-delete'){state.content='history';draw();toast('静态演示：对话删除后的返回位置');return;}
 if(name==='toggle-enabled'){state.enabled=!state.enabled;state.playing=false;state.complete=false;state.generation++;draw();return;}
 if(name==='toggle-speak'){state.autoSpeak=!state.autoSpeak;draw();return;}
 if(name==='open-settings'){state.view=state.enabled?'settings':'disabled';draw();return;}
 if(name==='close-settings'){state.view=state.enabled?'capsule':'hidden';draw();return;}
 if(name==='send'||name==='send-voice'){state.content='generating';state.playing=false;const generation=++state.generation;draw();setTimeout(()=>{if(generation!==state.generation||!state.enabled)return;state.content='chat';state.complete=state.view==='capsule'||['left','right'].includes(state.view);state.draft='';draw();},1400);return;}
 if(name==='stop-generation'){state.generation++;state.content='chat';draw();toast('已停止本地状态演示');return;}
 if(name==='play'){state.playing=!state.playing;el.classList.toggle('voice-playing',state.playing);el.setAttribute('aria-label',state.playing?'停止播报':'播放这条回答');el.innerHTML=icon(state.playing?'stop':'play');toast('设计原型：不调用真实扬声器');return;}
 if(name==='citation'){toast('固定版本引用入口：示例资料第4–6页');return;}
 if(name==='copy'){toast('复制回答入口（静态示例）');return;}
 if(name==='verify'||name==='retry'){toast('静态状态示例，未发出网络请求');return;}
 if(name==='mic-help'){toast('正式实现由F引导至系统或浏览器权限设置');return;}
}
function bind(){
 document.querySelectorAll('[data-action]').forEach(el=>el.addEventListener('click',()=>action(el.dataset.action,el)));
 const drag=document.querySelector('[data-drag]');
 if(drag&&state.view!=='full'&&state.view!=='theme'){
  drag.addEventListener('pointerdown',e=>{
   if(e.button!==0||drag.dataset.drag==='panel'&&e.target.closest('button'))return;
   const host=drag.closest('.assistant-panel,.capsule,.dock');const surface=document.querySelector('.surface');if(!host||!surface)return;
   const r=host.getBoundingClientRect(),p=surface.getBoundingClientRect();const start={x:e.clientX,y:e.clientY,left:r.left-p.left,top:r.top-p.top};let moved=false;
   const move=ev=>{const dx=ev.clientX-start.x,dy=ev.clientY-start.y;if(!moved&&Math.hypot(dx,dy)<8)return;moved=true;host.setPointerCapture?.(e.pointerId);host.style.left=Math.max(-64,Math.min(start.left+dx,p.width-r.width+64))+'px';host.style.top=Math.max(8,Math.min(start.top+dy,p.height-r.height-8))+'px';host.style.right='auto';host.style.bottom='auto';ev.preventDefault();};
   const up=ev=>{host.removeEventListener('pointermove',move);host.removeEventListener('pointerup',up);host.removeEventListener('pointercancel',up);if(!moved)return;state.suppressUntil=Date.now()+350;const b=host.getBoundingClientRect();state.playing=false;if(state.content==='recording')state.content='chat';if(b.left-p.left<=16||p.right-b.right<=16){state.previousView=state.view==='panel'?'panel':state.previousView;state.view=b.left-p.left<=16?'left':'right';state.position=null;}else{state.position={x:b.left-p.left,y:b.top-p.top};}draw();};
   host.addEventListener('pointermove',move);host.addEventListener('pointerup',up);host.addEventListener('pointercancel',up);
  });
 }
}
if(typeof module!=='undefined')module.exports={VERSION,SCREENS,PALETTES};
if(typeof document!=='undefined'){
 const id=new URLSearchParams(location.search).get('screen')||'web-dialog';active=SCREENS.find(x=>x.id===id)||SCREENS[1];
 state={mobile:active.platform==='Android',view:active.view,content:active.content,theme:active.theme,enabled:active.view!=='disabled',autoSpeak:true,complete:active.content==='complete',draft:'',position:null,previousView:'panel',playing:false,suppressUntil:0,generation:0,contextChosen:active.content!=='context'};
 draw();document.title=`${active.title} · 安研通 · ${VERSION}`;
 window.__assistantDesign={getState:()=>({...state}),setView:(view)=>{state.view=view;draw();},setContent:(content)=>{state.content=content;draw();},setTheme:(theme)=>{state.theme=theme;draw();}};
 window.addEventListener('resize',applyPosition);
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();if(['settings','disabled'].includes(state.view)){action('close-settings');return;}if(['history','delete','clear'].includes(state.content)){action('chat');return;}if(state.view==='full'){action('shrink');return;}if(state.view==='panel')action('collapse');}if(e.key==='Tab'){const modal=document.querySelector('.settings-card');if(!modal)return;const list=[...modal.querySelectorAll('button,input,textarea')].filter(el=>!el.disabled);const first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){last.focus();e.preventDefault();}else if(!e.shiftKey&&document.activeElement===last){first.focus();e.preventDefault();}}});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){state.playing=false;if(state.content==='recording'){state.content='chat';draw();}}});
}
