# AI 聊天分工入口

按 A–G 七个职责组织，最多四个同时推进。本聊天为唯一 A，本轮先并行新 B/C/D 工作树；共同基线与顺序见 [A2 开工](../a2-start.md)。A1 与 checkpoint-1 标签保留为历史。

复制下表任务书给对应聊天，打开自己的 worktree。底座证据见 ../a1-handoff.md；当前准备状态用 workflow.py status 核对。新树使用 [共享环境](../shared-environment.md)，不重复生成配置或自行升级依赖。

| 角色 | 任务书 | 工作区 |
|---|---|---|
| A | [总控与架构](A-integration.md) | 主目录 |
| B | [账号与业务管理](B-core.md) | Git 登记的外部树，codex/b-core-a2 |
| C | [内容与 AI](C-content-ai.md) | Git 登记的外部树，codex/c-content-ai-a2 |
| D | [学习体验与设计系统](D-learning-ui.md) | Git 登记的外部树，codex/d-learning-ui-a2 |
| E | [监控与风险反馈](E-monitoring.md) | others/worktrees/monitoring |
| F | [Windows 与安卓](F-clients.md) | others/worktrees/clients |
| G | [独立验收](G-qa.md) | others/worktrees/qa |

分支和可写范围以 ../../contracts/ownership.json 为准。通用每轮规则以根 AGENTS.md 为准。仅当前角色范围内写代码，共享契约、依赖入口与迁移交给 A。

已验收的三端底座继续使用；本轮 A2 集成 B/C/D，C 的语音配合 A 的最小原生接入。E/F 在后续空位扩展监控和完整原生打包，G 集成后独立实测。两位负责人分别审核集成/业务和内容/体验。

更新 baseline 后，各聊天在干净的本分支 merge main。每轮报告分支、提交 ID、检查证据和剩余事项。修改接口前先说明契约需求，由 A 协调。

新增需求以设计第11节为准：D1 先交三角色框架，B/C 可并行做后端；C 主责课件检索，D 提供三角色搜索入口，B/C/E 各自实现所属列表搜索，F/G 做原生适配与隔离验收。每次功能合并更新一键入口并实测；A 只在当前、B/C/D完成后的第二轮、第三轮三个节点推送，详见 ../git-workflow.md。
