# 契约入口

产品范围已经确认，实际 API、数据库迁移和生成客户端尚未落地。此目录是 A 维护的统一契约源；当前文档属于开工约定，不表示 OpenAPI 已冻结。

- domain-model.md：待实现的领域对象与不变量。
- api-conventions.md：三端接口与任务约定。
- ownership.json：角色分支与路径归属，工作区工具直接读取。

A1 发布门槛：锁定来源与依赖，建立最小授权模型和初始迁移，导出已实现接口的真实 OpenAPI 并生成客户端，记录 version.json。网页、Windows 测试包和安卓模拟器实际登录同一 PostgreSQL 后端后，发布对应 main SHA。未实现接口只留设计，不生成假成功接口。

领域聊天先提出契约变更请求，写清用途、字段、权限、旧新行为和兼容影响。A 将持久模型、迁移、实现、OpenAPI 与生成客户端作为一致变更集发布，给出契约版本和基线 SHA；消费者同步该基线后再实现依赖。优先兼容新增，破坏性变更明确受影响角色与同步批次。已发布版本和历史成绩不可随编辑题目而变化。

前端入口和公共路由由 D 维护，后端总入口及领域路由挂载由 A 维护。B 拥有 core 与 learning 后端，负责 Assignment/Assessment、Attempt/Answer、LearningProgress、TrainingRecord；C 提供审核发布的固定题目版本，D 调用服务端学习接口。
