# D-UI 第一批交接

2026-10-22，原D / codex/d-learning-ui-a2，基于98dace30e7786a6466cbf264996627097afffcde（ui-assistant-design-ready），真实契约保持0.3.1。执行记录核验为gpt-6.1-sol/xhigh；未修改全局配置。此文件随D交付提交保存，完整提交SHA以Git及最终交接报告为准，避免自引用。

## 本批交付与验证

- 统一导出、属性、布局归属及B示例见同目录README.md；逐项功能保留矩阵见feature-retention.md。
- 正式HashRouter及PageRegistration接入B教学/管理页面，包括教学班参数路由。公共壳不导入开发harness；教师/管理员页面展示与业务钩子原样保留。
- 登录/服务连接、服务端确认身份、强制及普通改密后重登、退出失败清本地、401/撤权/切身份和迟到响应处理。
- 学生账号邀请核验、合法专业、自设密码、独立学号；注册后手动登录；无效/撤销/过期/耗尽及同键恢复可验证。
- 本人资料通过GET/PATCH profile，性别/联系方式之外只读，提交真实revision，409后重读并提示核对。
- 学生授权教学班列表、中文关键词搜索、分页、刷新、待发布状态。显示真实总数，不增加学习进度、成绩或虚构统计。
- 原创SVG、Noto Sans SC原字体、来源及OFL迁入产品assets。OFL由正式入口引用并随dist分发。冻结设计与助手冻结资料保持原字节。

本树执行 pnpm run check、pnpm run build:web，以及 pnpm --filter @safelab/web exec playwright test tests/d-learning。11项浏览器检查覆盖三身份/正式B导航、教学班名单审批协作、强制改密/旧token失效、兼任收窄/撤权、邀请状态/非法专业、重复点击、资料冲突、真实分页、重登直链、手机真实触控、对话框键盘圈定、离线/远端退出失败、401/服务地址变化、同身份IME/查询竞态、注册响应丢失后的同键恢复。仅使用独立合成账号、专业、课程及邀请；固定演示账号密码不改。

额外用 node tests/d-learning/production.mjs 验证真实web/dist：来源匹配、包内字体/OFL、无公网资源请求、未配置状态、正式包拒绝调试HTTP及1440/390布局。正式包未配置时不发出业务API调用。报告/截图在当前树others/reports/d-ui/；browser-services.json分别记录D网页与A API的SHA、树标识、内容指纹及契约；production.json记录dist与当前D源码的一致性。提交后再次运行这些检查，最终证据以提交后的报告为准。

截图包括login、student-courses、registration、profile、identity-dialog、first-password、offline及production-unconfigured；390另有首屏图，完整长页图不代替固定底栏首屏。已经检查1440和390真实截图及溢出。浏览器响应式不是Windows/安卓原生验收。

## 接续与功能边界

A验证合并后发布组件基线，B再保留本树提交并合并该基线，迁移admin/teaching展示。B保持真实请求、会话、查询竞态、幂等、revision及权限规则；基础组件不反向导入B。之后交D二次整合，再由A/F验收既有UI。

学生加入/退出班级、申请及撤销在D二次整合补齐，必须在既有UI验收前完成。本批不把这些后续入口称为已完成。C/B2新增内容、六关、考试、进度和记录仍待A放行；监控、正式发布/云更新分别留E/F/A。助手当前未开放，不注册独立助手PageRegistration；未来D唯一宿主、C内容/历史/语音、F原生、B2账号级考试限制的职责均保留。

## 需A维护的公共事项（D未越界修改）

1. others/docs/ai/D-learning-ui.md旧完整Goal中“注册C助手页”的残余语义统一为唯一应用内悬浮宿主；保持对话、历史、引用、录音确认与播报任务。
2. C开工前落实云API与本地ASR worker的部署位置、鉴权、连接、超时与清理方式；不得把独立worker示例当成三端语音链路。
3. 将包内OFL/source.json信息补入others/licenses统一归档。D已确保所用OFL随dist分发，未越界修改A许可目录。
4. web/tests/foundation.spec.ts保留原业务检查并适配新入口：登录标签“账号/密码”改为“登录账号/登录密码”，动作“登录学习空间”改为“登录”；成功依据当前身份真实h1，退出后为“欢迎使用安研通”。教师创建改走正式“课程与教学班→新建课程与首班”及现有B表单；不再依赖旧App课程弹窗和“每一次实验，都从安全开始”标题。该公共旧测试本批未冒称通过，也未删除/修改。web/tests/shared/session.spec.ts与公共测试配置保持原字节。
5. profile及me当前仅有major_id，没有面向学生的专业名称查询。当前只读显示现有专业编号；如需可读专业名称，由A/B兼容扩充自助资料DTO后D接入，不拼造名称或调用管理员接口扩大权限。

当前无本批功能阻塞项；上述公共协调、B展示迁移、D二次整合及原生验证分别交接，不计入本批已完成范围。不推送、不建立新D树、不修改其他工作树或B后端/页面。
