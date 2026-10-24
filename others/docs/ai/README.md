# 六个协作身份与阶段Goal

先读[统一协作规范](../coordination.md)与[工作包模板](work-package-template.md)。v2由责任角色自查及编制工作包，普通已授权任务自主续办，重大事项判断后集中交A决策；C-01/C-02沿用既有约定，C-03起用新制。E监控整域已并C，F原生已并A副，旧任务书仅历史保留；G按里程碑启用，A副计入四聊天并行上限。

唯一A负责集成，最多四聊天并行容量。B1、D-UI和B展示迁移已接收，既有UI及[云端API/ASR前置](../cloud-asr-handoff.md)已通过A验收，c-start-ready允许C开工，B2仍等C交付经A接收后另行放行。D第二批Goal已交付，不重复运行；完整顺序以[阶段入口](../a2-start.md)为准，容量不意味着同时启动全部角色。

| 角色 | 任务与完整可复制Goal | 分支 |
|---|---|---|
| A主 | [总控与接收](A-integration.md) | main |
| A副 | [受托执行与原生客户端](executor.md) | codex/a-executor |
| B | [B-UI配合、历史B1及后续B2 Goal](B-core.md) | codex/b-core-a2 |
| C | [内容题库与助手Goal](C-content-ai.md) | codex/c-content-ai-a2 |
| D | [当前D-UI及C/B2后的完整D Goal](D-learning-ui.md) | codex/d-learning-ui-a2 |
| G | [独立验收](G-qa.md) | task/qa |

[C-02公共接入工作包](c02-public-integration.md)承接C的M1冻结候选，登记为planned；A副须等A明确启用及公布完整执行SHA后开工，当前不自动唤醒。未验证的候选先在独立集成树接入，不直接进main；C等待实际技术基线进入M2，完成C-02后停止。

读取根AGENTS、[A2开工](../a2-start.md)、[共享环境](../shared-environment.md)、[公共协议](../../contracts/a2-protocols.md)。A0检查见[交接报告](../a0-handoff.md)。各角色按Git登记自己的树；仅当前所有权代码/测试/提案/交接，公共变更交A，D唯一入口路由。B/C普通页面通过PageRegistration输出；助手按[已批准v1.1交接](../assistant-floating-handoff.md)由D唯一宿主承载C内容/历史/语音，不再注册独立聊天页，无第二套登录。该设计接收不提前放行C/B2或当前D-UI的助手新功能。

临时ui-design-v1见[UI协作与批准](../ui-redesign-coordination.md)及[辅助任务登记](../../contracts/auxiliary-tasks.json)，只修改设计资料前缀，不增加业务角色或接管D。所有UI设计使用frontend-design和批准规范；常规新页沿用风格自主设计/自查，不逐页等待审美批准。当前模型/强度与设置核验统一遵循协作规范，不以文字冒充已切换。

每轮相关检查后本地commit，合并后的里程碑完成时向A主简报完整SHA、事实和未完成，普通简报不等回执；子角色不推送，A主仅既有里程碑推送。D网页完成不代表原生验收；A2重建/九组合/真实录音后才checkpoint-2，C后续阶段扩展监控、A副受托扩展原生及正式发布准备。G仍独立验收。
