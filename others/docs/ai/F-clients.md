# F：Windows 与安卓任务书

**独立身份已停用。当前接收方：A副A-executor。** 不再复制下文旧Goal开工，也不在旧分支提交；历史树/分支与任务要求保留。当前职责、模型和门禁见[统一协作规范](../coordination.md)。以下为历史任务范围，不构成新增授权。

本次既有UI专项按[批准门禁](../ui-redesign-coordination.md)，在A明确交接且D/B实现后配合原生适配和重建实测；候选未批准时不迁移产品。三端复用共享前端，正式资源不依赖设计树，不建立三套独立界面。F目标xhigh，启用时核验实际设置；涉及UI设计必须frontend-design及冻结规范，常规新页自主设计/截图自查。完整原生能力及正式发布仍按A后续阶段安排。

当前UI-2026.10-v1已批准并接收冻结d17b342c53fc054bd298bee356143d3b3ab77af6，先保存本树改动并合并A的ui-redesign-ready以读取[执行交接](../ui-redesign-execution.md)及platform-spec；D/B真实界面经A集成后再接原生验证。Windows缩放、Android安全区/软键盘/返回/文件交互必须在新包中实测；当前设计浏览器记录不作为这些结果。

请作为 SafeLabPlatform 的 F 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，A1 的实际实现、验收状态与可交接基线见 others/docs/a1-handoff.md；后续模块按已发布基线继续开发。

## 开始前

助手后续原生适配以[已批准v1.1交接](../assistant-floating-handoff.md)和platform-spec为准，等C/D经A集成后再开始。F通过现有桥接验证真实麦克风/TTS、后台停止、键盘、安全区、返回优先级及Windows缩放；复用D唯一应用内宿主，不增加跨软件系统悬浮权限或另一套状态。计划max、执行xhigh，开工核验实际设置，本次不自动唤醒或放行新增功能。

1. 打开自己的独立工作区 others/worktrees/clients，确认当前分支为 task/clients。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 当前基线为 checkpoint-1，包含最新一键工具及三角色/搜索要求；从交接报告核对后，在干净的本分支合并并确认 contains_baseline=true 再开始实现。

## 本角色任务

1. 接管 A1 已建立的 Electron 与 Capacitor 工程，复用共享网页产物和生成客户端，扩展实际能力。
2. 实现可配置服务地址、安全凭据、文件选择、麦克风/摄像头及返回键适配。
3. 维护 A1 已通过的构建命令，扩展 Windows 正式安装器、安卓 release 签名和发布流程。
4. 实机检查登录、三角色、录音、上传和网络；干净目录运行时不依赖开发路径。
5. 验证三角色搜索在原生端的中文输入、键盘、筛选、返回、定位和文件打开；每次 A 功能合并协助重建两端产物、核对源码/契约版本和本轮一键入口。本端启动器由 F 维护，共用根入口或 others/scripts 的修改交 A 集成。

## 修改范围

- desktop/
- android/
- web/src/platform/

范围以 ownership.json 为准。前端公共路由交 D 注册；依赖、后端总路由、数据库迁移及共享类型变更交 A 集成，提出需求和兼容影响。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/clients；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
