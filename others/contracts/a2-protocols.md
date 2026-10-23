# A2 模块交接协议

当前角色合并见[协作规范](../docs/coordination.md)：历史F原生职责由A副受托接收，D仍唯一宿主；业务协议与既有门禁不因更名改变。

本文件是后续实现的约束，**不表示 HTTP 接口、业务 UI 或原生适配已完成**。共享 TypeScript 声明已经存在；实际字段变更先交 A，再随真实实现导出。

## 页面、身份及导航

A 维护 web/src/lib/api.ts、extensions.ts、lesson-protocol.ts 及生成 SDK。D 使用已锁定的 react-router 8.5.0 HashRouter，唯一维护 App/main/routes。B/C普通业务页面导出 PageRegistration[]：id/path/title/workRoles/component/navGroup；助手采用下述单例宿主适配，不导出独立聊天PageRegistration。PageProps 只有服务器用户/当前 SessionSnapshot、路由参数、navigate 和 PlatformBridge，不含 token、数据库或 AI 密钥。校验合法目的地和资源授权后导航；未知/无权限页面有独立状态。

D 在登录后调用 confirmSession；切换使用 switchWorkRole 后等待服务端确认，不仅切标签。订阅会话代次清除所有页面请求和查询；退出失败也清理本地并提示远端撤销失败。组件内搜索再处理同身份查询竞态。B/C 不导入 D 的入口或路由实现。

B/C在完整D路由前，用本角色所有权内的开发渲染夹具和独立测试配置验证页面组件，复用公共服务归属辅助并调用真实API，记录测试入口。该夹具不注册产品公共路由，不替代D集成，也不用假成功数据冒充业务。公开入口由D后续统一接入。

## 悬浮助手：已批准语义，待真实实现

本节依[UI-ASSISTANT-2026.10-v1.1交接](../docs/assistant-floating-handoff.md)补充既有协议。以下是行为语义，A在对应实现阶段统一正式公共类型和导出名；本次未发布占位HTTP或修改生成SDK。

D维护应用内唯一宿主/框架和个人设置；C提供助手内容、状态及动作，F提供PlatformBridge。展示状态 hidden/capsule/panel/fullscreen/docked_left/right 与业务 allowed/paused/unavailable/unconfigured 分开，个人enabled不授予服务端能力。导航唤起同一实例；关闭状态引导设置，手机全屏是布局变化，不创建独立对话路由。

D向C提供已确认SessionSnapshot/代次、当前有权教学班上下文、PlatformBridge及本设备播报偏好、请求展开/收起/完成提示回调；不传token或密钥。C向D提供内容视图、业务可用性、音频/任务状态、历史/新建、内部返回消费和停止/取消/清理回调，不创建第二fixed容器。返回先由C处理内部临时视图，再由D按全屏→小窗→胶囊，最后交A副原生适配/路由；业务阻塞弹窗高于助手且焦点不穿透。

打开意图为text/voice，可带当前授权course_id及显式conversation_id。新对话继承当前有权班，无班先选择；已有对话course_id固定，页面换班不改旧范围，引用固定资料版本和页段。C提供本人列表、读取、新建、继续、删除、清空，三端共用服务端文字历史；管理员不因此得到任意读他人私聊的权限。服务端每次按学校、本人账号、当前身份、教学班/资料授权和学生考试gate重新判定。退出后保留有权服务器历史，客户端清内容/草稿/缓存，撤权后不能继续读取旧私有信息。

收起/吸边停录音与TTS并保留已识别草稿，文字问答可继续，仅提示完成，不自动展开或播报；设置关闭则取消/失效本地请求并尽力取消远端。退出/切学校、服务或身份立即推进代次并清理，不等待远端取消。C所有晚到正文/音频、D完成提示都核对有效会话/请求代次；删除或清空后旧任务不能复活对话。

个人UI偏好只按本设备profile、规范化服务origin、school_id、user_id保存开关/外壳/位置/播报；本地不持久化消息、录音、Bearer或密钥。刷新从胶囊开始，不恢复活动音频；存储失败明确说明仅本次有效。录音显式开始→真实ASR→可编辑文字确认→问答；文字手动播报，语音自动播报须窗口展开、应用前台、偏好开启、会话/请求有效且gate仍allowed。收起/后台/考试暂停/身份变化立即停音频，恢复不自动续播。

学生账号任一有效正式考试暂停问答、历史、引用、旧会话和所有任务阶段；未知状态同样暂停。D移除当前渲染树中的历史/回答并使缓存失效，C在服务端及结果返回再次验证；恢复须服务端确认allowed后重新读取，不直接展示旧缓存。C阶段B2未就绪仍以教师验证，学生不可用，既有UI验收门禁保持不变。

## 内容及关卡

lesson-protocol.ts 的 schema_version=labconnect.lesson/1。StudentLesson 有 lesson_id/version_id/title/short_lesson/required/scene/activities，不含答案。活动用稳定 id，choice（单/多选）、hotspot（0–1归一化矩形、SVG viewBox坐标映射）、order（稳定选项顺序）可组合；发布时验证 ID 唯一、引用有效、坐标合法及安全 SVG，数量不能写死。

TeacherLessonPreview 包装独立 review/correct_ids/explanation，只有授权教师/管理者接口能返回。C 的 LessonEditorProps.renderPreview 接收此 DTO，由 D 集成注入渲染器；C 不反向导入 D 学生功能。预览不产生 Attempt、LearningProgress、成绩、徽章或培训记录。教师答案禁止塞入学生 DTO 或只用 CSS 隐藏。

六个原创二维示范主题：通识的“入室与个人防护、设备用电与行为规范、应急处置”；化学的“试剂标签与储存、操作与通风、废物与泄漏应对”。默认每班三关按序解锁，练习可反复纠错，全部必修互动服务端确认才过关。C 管内容/版本，B2 管正式互动答案/进度/徽章，D 管键盘触屏渲染；AI 生成新关卡本轮只预留扩展，不能称完成。

平台公共库、学校库、学院、目录共享和班级私有分别授权。教师提交目录共享版本，目录负责人或有范围管理员审核；私有/草稿不自动共享。引用固定发布版本，复制形成新草稿。C 提供 B2 内部读取已审核题目/答案的受控服务；学生路径无原始答案。

## 考试与辅导限制

B2 实现 Assignment/Assessment、Attempt/Answer、自动保存/续答、超时结算和幂等提交。发布快照固定题目、答案、关键题、分值、时限（默认60分钟）、最多次数（默认3）、及格线（默认80）、关卡条件和记录有效期（默认12个月），教师仅发布前可调。多选全对，否则0；最高成绩展示与同次达标分开计算。关考后由教师统一公布答案解析。

开始接口复用当前有效 attempt，不因重复请求/刷新/重登占次；事务/锁阻止并发超次。保存使用 answer_revision，返回 saved_at/deadline/server_time；过期/冲突明确拒绝。页面关闭不暂停；超时按服务端已保存答案结算，断网只留当前页内存、不伪称保存。历史内容和评分不被新版本改写。

B2 给 C 提供 account-level tutoring gate，语义为 allowed/paused/unavailable、as_of、有效进行中作答；学生任一有效正式考试即暂停该账号全部平台 AI 辅导。C 在文字、语音识别后问答、旧对话续问、历史/引用读取、跨班请求、任务开始/执行/返回都验证。状态不可核实暂停学生辅导；其他账号不受影响。提交/到期/教师合法中止重算，其他考试仍在则继续暂停。C 阶段 B2 未实现时教师账号完成真实验收，学生明确不可用；B2 再联合验收，不把后续依赖设成 C 完成的循环前置条件。

## 服务端 AI 配置

app/core/providers.py 已提供 ProviderSpec、EncryptedProfile、SchoolProviderSelection、seal_key/open_key、resolve_provider、不可变 ProviderSnapshot、can_manage_school_provider。C 复用，不另建一套加密；C 实现 DB持久化、配置管理/测试/启用/审计和管理员设置页，A 接迁移、公共挂载和 SDK，D 接路由。

学校主动选择 unconfigured/platform/school。学校管理员且当前 administrator 身份才可管本校；学院管理员无此权限。platform 模式使用平台完整配置；school 模式自有地址/模型/密钥必须成组绑定，禁止继承平台密钥到新地址。ProviderSpec 当前支持 openai-chat + HTTPS；本地 HTTP 推理若确需启用先由 A 增加平台控制的本机地址白名单，学校不能任意放开 HTTP/内网目标。C 的云连接器还需由平台策略控制目标与重定向，不能让可配置地址读取内网服务。

新配置产生 revision，服务端完成连接与业务字段结构验证，记录 tested_revision 才允许启用；失败保持旧启用版。新任务只捕获一次完整不可变快照（学校选择版本和实际供应商版本都记审计），已开始任务不混用新地址/模型/密钥。平台默认更新也先测再启用；学校已明确选 platform 才跟随默认。主密钥与密文分开备份在忽略区，学校与版本为 AES-GCM AAD，前端仅 public_status 掩码，不返回 ciphertext。model_dump 默认含密文，必须显式使用 public_status，不能直接序列化持久模型。

当前已授权的开发配置为 DeepSeek 官方 https://api.deepseek.com、deepseek-flash；A0限量真实请求上限3次、每次输出≤512 token、关闭思考，不调用Pro。实际 Pro 接口名当前为 deepseek-v4-pro（2026-10-21 官方文档），正式学校可自行配置受支持名称，不硬编码 Pro 或静默映射 deepseek-pro。以后连接测试需重新以相应任务授权与预算执行；A0探针不作为常规后台自动请求。

## 音频、文件与原生能力

业务 Python 3.14 与 ASR worker Python3.13分离，共用一份 CPU sherpa-onnx1.13.8 / Paraformer 缓存，来源哈希见 others/ai_worker/models.lock.json。C 校验真实 WAV 头、声道1、16kHz、PCM16、长度/大小；不把 WebM 改后缀当 WAV。C 完成识别、文字确认、检索问答及系统 TTS 协作；独立 worker 示例识别不等于网页/Windows/安卓采集完成。

A已发布[cloud-asr-handoff](../docs/cloud-asr-handoff.md)的内部labconnect-asr-1适配：app.core.asr_client.AsrClient，最多30秒/964096字节、单推理、独立服务key、取消/超时回收子进程、结果TTL60秒。云端走SSH Unix套接字，本机角色树复用A的loopback配置；没有新增公共HTTP或SDK。C绑定业务task/授权/考试gate，服务地址与key只由A基础设施配置，不作为学校AI地址或前端参数；A维护transport/，C保持speech/content所有权。

PlatformBridge 约定 permission/start/stop/cancelRecording、speak/stopSpeaking、openCitation、downloadMaterial。采集不满足格式时用真实解码/重采样，失败明确反馈。先显示识别文字供用户确认才发送问答，支持取消和停止；原始录音处理后默认删除。原生权限/文件选择/下载/引用跳转由 A/F 在 C/D 交付后适配并逐平台实测，本轮只声明协议。

问答仅检索当前有权且允许云处理资料，引用固定版本页/段落；资料不足明确说明。无模型、配额/网络/设备失败及中文语音不可用均真实反馈。原始监控媒体不发送云端，E只交去身份事件摘要；合成摘要可测草稿，不能称完整监控已完成。
