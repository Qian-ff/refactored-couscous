# AI 聊天分工与阶段Goal

唯一A负责集成，最多四聊天并行容量。B1和D-UI第一批公共组件已接收，当前B从[d-ui-components-ready组件基线](../d-ui-foundation-handoff.md)迁移所属展示层，随后D二次整合、A/F既有UI验收，再进入C/B2。完整顺序以[阶段入口](../a2-start.md)为准，容量不意味着同时启动全部角色。

| 角色 | 任务与完整可复制Goal | 分支 |
|---|---|---|
| A | [公共底座及集成](A-integration.md) | main |
| B | [B-UI配合、历史B1及后续B2 Goal](B-core.md) | codex/b-core-a2 |
| C | [内容题库与助手Goal](C-content-ai.md) | codex/c-content-ai-a2 |
| D | [当前D-UI及C/B2后的完整D Goal](D-learning-ui.md) | codex/d-learning-ui-a2 |
| E | [完整监控](E-monitoring.md) | task/monitoring |
| F | [原生适配与发布](F-clients.md) | task/clients |
| G | [独立验收](G-qa.md) | task/qa |

读取根AGENTS、[A2开工](../a2-start.md)、[共享环境](../shared-environment.md)、[公共协议](../../contracts/a2-protocols.md)。A0检查见[交接报告](../a0-handoff.md)。各角色按Git登记自己的树；仅当前所有权代码/测试/提案/交接，公共变更交A，D唯一入口路由。B/C普通页面通过PageRegistration输出；助手按[已批准v1.1交接](../assistant-floating-handoff.md)由D唯一宿主承载C内容/历史/语音，不再注册独立聊天页，无第二套登录。该设计接收不提前放行C/B2或当前D-UI的助手新功能。

临时ui-design-v1见[UI协作与批准](../ui-redesign-coordination.md)及[辅助任务登记](../../contracts/auxiliary-tasks.json)，只修改设计资料前缀，不增加业务角色或接管D。所有UI设计使用frontend-design和批准规范；常规新页沿用风格自主设计/自查，不逐页等待审美批准。计划阶段max；执行A=max、B–F及设计=xhigh，G保持原安排；实际轮次单独核验，不能以规则文字冒充已切换。

每轮相关检查后本地commit，报告完整SHA、事实和未完成；子角色不推送，A仅既有里程碑推送。D网页完成不代表原生验收；A2重建/九组合/真实录音后才checkpoint-2，E/F后续扩展监控/正式发布。两位负责人分别复核业务集成和内容体验。
