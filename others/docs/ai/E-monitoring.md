# E：监控与风险反馈任务书

请作为 SafeLabPlatform 的 E 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，A1 的实际实现、验收状态与可交接基线见 others/docs/a1-handoff.md；后续模块按已发布基线继续开发。

当前按[阶段门禁](../a2-start.md)等待A安排，不因UI设计支线登记启动监控新业务。E目标xhigh，启用时核验实际聊天设置；新增或修改告警等UI必须使用frontend-design并读取[批准规范与规则](../ui-redesign-coordination.md)，常规新页沿用风格自主设计/截图自查。产品入口由D统一注册，保持E所有权。

## 开始前

1. 打开自己的独立工作区 others/worktrees/monitoring，确认当前分支为 task/monitoring。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 当前基线为 checkpoint-1，包含最新一键工具及三角色/搜索要求；从交接报告核对后，在干净的本分支合并并确认 contains_baseline=true 再开始实现。

## 本角色任务

1. 实现上传视频与一路实时设备摄像头、本地预览和授权证据回看。
2. 验证人员计数、区域阈值和持续超员；验证烟雾/火焰模型、平滑与去重。
3. 实现疑似、确认/排除、关闭、日志、队列和失败处理。
4. 只向云 AI 提交去身份事件摘要；与 C 的案例草稿接口对接。
5. 建立独立样例评估，记录误报、漏报、延迟与资源；未合格保持实验性标识。
6. 实现授权实验室范围内的告警搜索和日期/状态/类型筛选，先鉴权再计数与分页；学生搜索和选课不授予监控或原始媒体访问权限。搜索组件与入口和 D 协调。

## 修改范围

- others/backend/app/domains/monitoring/
- others/ai_worker/monitoring/
- web/src/features/monitoring/

范围以 ownership.json 为准。前端公共路由交 D 注册；依赖、后端总路由、数据库迁移及共享类型变更交 A 集成，提出需求和兼容影响。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/monitoring；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
