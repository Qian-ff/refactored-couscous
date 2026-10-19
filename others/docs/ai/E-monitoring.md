# E：监控与风险反馈任务书

请作为 SafeLabPlatform 的 E 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/monitoring，确认当前分支为 task/monitoring。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 实现上传视频与一路实时设备摄像头、本地预览和授权证据回看。
2. 验证人员计数、区域阈值和持续超员；验证烟雾/火焰模型、平滑与去重。
3. 实现疑似、确认/排除、关闭、日志、队列和失败处理。
4. 只向云 AI 提交去身份事件摘要；与 C 的案例草稿接口对接。
5. 建立独立样例评估，记录误报、漏报、延迟与资源；未合格保持实验性标识。

## 修改范围

- others/backend/app/domains/monitoring/
- others/ai_worker/monitoring/
- web/src/features/monitoring/

范围以 ownership.json 为准。前端公共路由交 D 注册；依赖、后端总路由、数据库迁移及共享类型变更交 A 集成，提出需求和兼容影响。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/monitoring；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
