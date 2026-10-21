# 契约入口

A 维护统一契约。实际接口以 openapi.json、version.json 和生成客户端为准；当前为 **0.3.1**。版本唯一来源是 ../config/application.json，应用 OpenAPI、health 与导出工具共同读取。A0历史基线0.2.0及B1首次基线0.3.0保留。

0.3.0 在A0底座上增加真实组织/专业/账号/授权/改密、目录与班级管理/审批/交接、CSV导入等B1路由。模型注册、兼容迁移和生成SDK已交接，历史见[B1公共交接](../docs/b1-public-handoff.md)。B1最终领域及独立业务组件见[B1集成交接](../docs/b1-handoff.md)，正式导航由D接入；内容/助手/考试/记录接口未发布。

0.3.1 增加真实GET /catalogs/{catalog_id}/teacher-options及生成方法TeachingService.catalogTeacherOptions。已有目录的负责人可指定本校主教师开班，仍无该班私有数据权限；无catalog_id的旧请求保持本人首班限制。无新模型或迁移。

- [领域不变量](domain-model.md)：已实现对象及后续业务规则。
- [接口约定](api-conventions.md)：鉴权、版本、错误和幂等。
- [后续模块协议](a2-protocols.md)：明确标为设计的内容、考试、关卡、页面和平台能力交接。
- ownership.json：机器读取的角色、分支与路径。
- [临时辅助任务登记](auxiliary-tasks.json)：设计支线范围、候选及批准/冻结状态；不改变七角色所有权，流程见[UI协作](../docs/ui-redesign-coordination.md)。
- [A0 检查与交接](../docs/a0-handoff.md)：运行证据与阶段边界。

领域角色先在自己的目录提交提案：用途、字段、权限、状态、旧新行为、兼容/迁移、依赖及页面注册需求。A 接收可集成实现后，统一发布模型注册、迁移、路由、真实 OpenAPI、SDK 和完整 SHA。消费者合并该基线再依赖新接口；设计协议不进入生成客户端。公共修改中途及时交接。

前端公共入口/HashRouter/路由唯一由 D 维护。B/C 的普通业务页输出独立组件及 PageRegistration 清单，使用 web/src/lib/extensions.ts；C 的关卡编辑器接受 renderPreview，由 D 集成注入。助手例外：C提供内容与生命周期适配器，由D唯一悬浮宿主承载，不注册独立聊天页，见[已批准交接](../docs/assistant-floating-handoff.md)。B 管核心/正式学习与考试，C 管固定内容版本/检索/助手；保持模块单向依赖。
