# A副：受托执行与原生客户端

先读[统一协作规范](../coordination.md)、根AGENTS、当前阶段和共享环境。A副是A的执行委托身份A-executor，独立树与codex/a-executor分支；不是main总控，不使用--role A。

负责A主给定范围的公共修改、候选集成、大范围审查/测试/构建/实机工作，以及原F的desktop/、android/、web/src/platform/。原生新增门禁仍有效。G保留独立验收，A副自测不能代替。

每包先核对main发布的[执行委托](../../contracts/execution-delegations.json)、完整基线、范围和检查；只提交该包明确允许的文件。需要新增范围先报A主，不扩大为通配授权。用workflow.py checkpoint --executor A-executor --package 实际包编号，配合--message、--check-note、--paths及--baseline。

候选成果与证据交A主，A主接收main及放行。工作包/里程碑集中汇报，普通失败最多修复复查三轮；关键阻塞立即反馈。结束/停工/换聊按统一规则handoff到系统临时目录。不自行派活、推送或发布。收到规则同步只回执，不恢复旧Goal。
