# 契约入口

A 维护统一契约。实际接口以 openapi.json、version.json 和生成客户端为准；当前为 **0.3.0**。版本唯一来源是 ../config/application.json，应用 OpenAPI、health 与导出工具共同读取。A0历史基线0.2.0保留。

0.3.0 在A0底座上增加真实组织/专业/账号/授权/改密、目录与班级管理/审批/交接、CSV导入等B1路由。模型注册、兼容迁移和生成SDK已交接，见[B1公共交接](../docs/b1-public-handoff.md)。B1完整界面仍在B交付范围；内容/助手/考试/记录接口未发布。

- [领域不变量](domain-model.md)：已实现对象及后续业务规则。
- [接口约定](api-conventions.md)：鉴权、版本、错误和幂等。
- [后续模块协议](a2-protocols.md)：明确标为设计的内容、考试、关卡、页面和平台能力交接。
- ownership.json：机器读取的角色、分支与路径。
- [A0 检查与交接](../docs/a0-handoff.md)：运行证据与阶段边界。

领域角色先在自己的目录提交提案：用途、字段、权限、状态、旧新行为、兼容/迁移、依赖及页面注册需求。A 接收可集成实现后，统一发布模型注册、迁移、路由、真实 OpenAPI、SDK 和完整 SHA。消费者合并该基线再依赖新接口；设计协议不进入生成客户端。公共修改中途及时交接。

前端公共入口/HashRouter/路由唯一由 D 维护。B/C 输出独立页面组件及 PageRegistration 清单，使用 web/src/lib/extensions.ts；C 的关卡编辑器接受 renderPreview，由 D 集成注入。B 管核心/正式学习与考试，C 管固定内容版本/检索/助手；保持模块单向依赖。
