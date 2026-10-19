# C：内容与 AI任务书

请作为 SafeLabPlatform 的 C 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/content-ai，确认当前分支为 task/content-ai。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 实现授权课件/知识点提取、来源页码/段落、内容版本和检索。
2. 实现生成题组草稿、增删改、局部/整组重生成、审核发布和题目版本。
3. 实现点击录音、识别文字确认、基于有权资料问答、出处和播报协作。
4. 实现模型适配、掩码配置、连接测试和学校覆盖的业务逻辑；配置公共入口由 A 集成。
5. 接收去身份事件摘要转案例草稿，发布必须经教师审核。

## 修改范围

- others/backend/app/domains/content/
- others/backend/app/domains/assistant/
- others/ai_worker/content/
- others/ai_worker/speech/
- web/src/features/content/
- web/src/features/assistant/

范围以 ownership.json 为准。前端公共路由交 D 注册；依赖、后端总路由、数据库迁移及共享类型变更交 A 集成，提出需求和兼容影响。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/content-ai；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
