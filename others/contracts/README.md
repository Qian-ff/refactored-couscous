# 契约入口

A 维护统一契约。实际接口以 openapi.json、version.json 和生成客户端为准；当前为 **0.2.0**。版本唯一来源是 ../config/application.json，应用 OpenAPI、health 与导出工具共同读取。A1 历史基线仍为 0.1.0。

0.2.0 已实现 CourseCatalog 兼容底座、Course.catalog_id、工作身份上下文、实时会话/授权检查与原账号/课程接口。模型集中入口、迁移、后端挂载、公共请求层和 SDK 由 A 维护。目录 CRUD、完整账号管理、内容/搜索/考试/任务接口仍由后续阶段实现。

- [领域不变量](domain-model.md)：已实现对象及后续业务规则。
- [接口约定](api-conventions.md)：鉴权、版本、错误和幂等。
- [后续模块协议](a2-protocols.md)：明确标为设计的内容、考试、关卡、页面和平台能力交接。
- ownership.json：机器读取的角色、分支与路径。
- [A0 检查与交接](../docs/a0-handoff.md)：运行证据与阶段边界。

领域角色先在自己的目录提交提案：用途、字段、权限、状态、旧新行为、兼容/迁移、依赖及页面注册需求。A 接收可集成实现后，统一发布模型注册、迁移、路由、真实 OpenAPI、SDK 和完整 SHA。消费者合并该基线再依赖新接口；设计协议不进入生成客户端。公共修改中途及时交接。

前端公共入口/HashRouter/路由唯一由 D 维护。B/C 输出独立页面组件及 PageRegistration 清单，使用 web/src/lib/extensions.ts；C 的关卡编辑器接受 renderPreview，由 D 集成注入。B 管核心/正式学习与考试，C 管固定内容版本/检索/助手；保持模块单向依赖。
