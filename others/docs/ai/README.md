# AI 聊天分工入口

按 A–G 七个职责组织，最多四个同时推进。先由 A 落地真实框架、授权模型和接口基线，再启动依赖模块。

复制下表对应任务书的全文给新聊天；打开该聊天专属 worktree。当前 main 是准备基线，不能把准备脚本当成应用。

| 角色 | 任务书 | 工作区 |
|---|---|---|
| A | [总控与架构](A-integration.md) | 主目录 |
| B | [账号与业务管理](B-core.md) | others/worktrees/core |
| C | [内容与 AI](C-content-ai.md) | others/worktrees/content-ai |
| D | [学习体验与设计系统](D-learning-ui.md) | others/worktrees/learning-ui |
| E | [监控与风险反馈](E-monitoring.md) | others/worktrees/monitoring |
| F | [Windows 与安卓](F-clients.md) | others/worktrees/clients |
| G | [独立验收](G-qa.md) | others/worktrees/qa |

分支和可写范围以 ../../contracts/ownership.json 为准。通用每轮规则以根 AGENTS.md 为准。仅当前角色范围内写代码，共享契约、依赖入口与迁移交给 A。

先由 A1 发布三端底座；之后并行 B/C/D。A2 负责集成，E/F 在相应基线可用后替换已完成轮次；G 可准备测试需求，集成后独立实测。两位负责人分别审核集成/业务和内容/体验。

更新 baseline 后，各聊天在干净的本分支 merge main。每轮报告分支、提交 ID、检查证据和剩余事项。修改接口前先说明契约需求，由 A 协调。
