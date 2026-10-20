# AI 聊天分工与阶段Goal

唯一A负责集成，最多四聊天并行容量；本轮业务交付顺序固定为 **A0→B1→C→B2联合验证→D→A2**。容量不意味着现在同时启动全部角色。A0完成后先执行B1，后续每段由A及时发布真实迁移/接口/SDK和完整SHA，不等整轮结束才协调。

| 角色 | 任务与完整可复制Goal | 分支 |
|---|---|---|
| A | [公共底座及集成](A-integration.md) | main |
| B | [B1、C后B2两份Goal](B-core.md) | codex/b-core-a2 |
| C | [内容题库与助手Goal](C-content-ai.md) | codex/c-content-ai-a2 |
| D | [三角色学习界面Goal](D-learning-ui.md) | codex/d-learning-ui-a2 |
| E | [完整监控](E-monitoring.md) | task/monitoring |
| F | [原生适配与发布](F-clients.md) | task/clients |
| G | [独立验收](G-qa.md) | task/qa |

读取根AGENTS、[A2开工](../a2-start.md)、[共享环境](../shared-environment.md)、[公共协议](../../contracts/a2-protocols.md)。A0检查见[交接报告](../a0-handoff.md)。各角色按Git登记自己的树；仅当前所有权代码/测试/提案/交接，公共变更交A，D唯一入口路由。B/C页面通过PageRegistration输出，无第二套登录。

每轮相关检查后本地commit，报告完整SHA、事实和未完成；子角色不推送，A仅既有里程碑推送。D网页完成不代表原生验收；A2重建/九组合/真实录音后才checkpoint-2，E/F后续扩展监控/正式发布。两位负责人分别复核业务集成和内容体验。
