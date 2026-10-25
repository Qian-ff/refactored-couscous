# 六个协作身份与阶段Goal

**v3当前任务入口**：[全项目路线/逐聊天交接](../delivery-workflow.md)、[A副1生效包](c02-public-integration.md)、[D1资料页主线接收](../material-ui-main-reception.md)、[C1专用迁移与PG接入T1](c1-schema-pg-integration.md)、[C1历史首次启动词](c1-question-lessons.md)、[G后续验收](qa-final-acceptance.md)。B2按固定内容版本/学生DTO/受控答案服务放行；以下旧Goal为历史/后续参考，角色与顺序以v3为准。

先读[统一协作规范](../coordination.md)与[工作包模板](work-package-template.md)。v2由责任角色自查及编制工作包，普通已授权任务自主续办，重大事项判断后集中交A决策；C-01/C-02业务证据保留，C02剩余工作转A副/D，C后续新模块首次手动启动。E监控backend/worker并C、前端并D，F原生已并A副，旧任务书仅历史保留；G按里程碑启用，A副计入四聊天并行上限。

唯一A负责集成，最多四聊天并行容量。B1、D-UI和B展示迁移已接收，既有UI及[云端API/ASR前置](../cloud-asr-handoff.md)已通过A验收，c-start-ready允许C开工，B2仍等C交付经A接收后另行放行。D第二批Goal已交付，不重复运行；完整顺序以[阶段入口](../a2-start.md)为准，容量不意味着同时启动全部角色。

| 角色 | 任务与完整可复制Goal | 分支 |
|---|---|---|
| A主 | [总控与接收](A-integration.md) | main |
| A副 | [受托执行与原生客户端](executor.md) | codex/a-executor |
| B | [B-UI配合、历史B1及后续B2 Goal](B-core.md) | codex/b-core-a2 |
| C | [内容题库与助手Goal](C-content-ai.md) | codex/c-content-ai-a2 |
| D | [当前D-UI及C/B2后的完整D Goal](D-learning-ui.md) | codex/d-learning-ui-a2 |
| G | [独立验收](G-qa.md) | task/qa |

[C-02公共接入工作包](c02-public-integration.md)承接C的M1冻结候选，已由v3登记active；A提交生效规则并发送完整SHA后A副开工。未验证候选先在独立树接入；A副与D完成剩余C02，不再交C进入M2。

读取根AGENTS、[A2开工](../a2-start.md)、[共享环境](../shared-environment.md)、[公共协议](../../contracts/a2-protocols.md)。A0检查见[交接报告](../a0-handoff.md)。各角色按Git登记自己的树；仅当前所有权代码/测试/提案/交接，公共变更交A，D唯一入口路由。B及D内容类普通页面通过PageRegistration输出；助手按[已批准v1.1交接](../assistant-floating-handoff.md)由D唯一宿主及前端适配接C内容/历史/语音服务，不再注册独立聊天页，无第二套登录。该设计接收不提前放行C/B2或当前D-UI的助手新功能。

临时ui-design-v1见[UI协作与批准](../ui-redesign-coordination.md)及[辅助任务登记](../../contracts/auxiliary-tasks.json)，只修改设计资料前缀，不增加业务角色或接管D。所有UI设计使用frontend-design和批准规范；常规新页沿用风格自主设计/自查，不逐页等待审美批准。当前模型/强度与设置核验统一遵循协作规范，不以文字冒充已切换。

每轮相关检查后本地commit，合并后的里程碑完成时向A主简报完整SHA、事实和未完成，普通简报不等回执；子角色不推送，A主仅既有里程碑推送。D网页完成不代表原生验收；A2重建/九组合/真实录音后才checkpoint-2，C后续阶段扩展监控、A副受托扩展原生及正式发布准备。G仍独立验收。
