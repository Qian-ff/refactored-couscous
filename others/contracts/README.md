# 契约入口

## 0.5.0 C1主线源码（运行激活待P2）

T2接入实际题库/关卡教师管理路由、导入二进制PUT及鉴权Blob导出，唯一版本源为application.json 0.5.0。A已统一接收最终T2及P1工具；候选检查来源以A副 `others/reports/c1-public/t2/` 最终清单为准，原主库迁移、共享环境和三端产物仍待P2实测，见[主线接收](../docs/c1-main-reception.md)。C02既有VersionView/ReviewView等TS名称由生成器命名规则保持，D无需为同名C1 DTO改页面。

B2内部受控服务为 `questions.assessment.resolve_assessment_questions`、`lessons.assessment.resolve_lesson_publication`；生成客户端中的StudentLesson来自真实教师预览模型，不新增学生答案接口。学生投影只过滤数据，不代替B2真实任务/关系/解锁授权。D消费实际TeacherLessonPreview和StudentLesson，暂不启动D2页面。

现行六身份及E/F接收方见[统一协作规范](../docs/coordination.md)；仅协作身份变更，不改业务API版本。A副具体写范围见[执行委托](execution-delegations.json)。

A 维护统一契约。实际接口以 openapi.json、version.json 和生成客户端为准；main源码现行契约为 **0.5.0**，包含资料/有权正文检索及C1题库关卡管理；运行、客户端和ECS版本须分别看A实际发布记录。版本唯一来源是 ../config/application.json，应用 OpenAPI、health 与导出工具共同读取。A0历史基线0.2.0及B1首次基线0.3.0保留。

0.3.0 在A0底座上增加真实组织/专业/账号/授权/改密、目录与班级管理/审批/交接、CSV导入等B1路由。模型注册、兼容迁移和生成SDK已交接，历史见[B1公共交接](../docs/b1-public-handoff.md)。B1最终领域及独立业务组件见[B1集成交接](../docs/b1-handoff.md)，正式导航由D接入；内容/助手/考试/记录接口未发布。

0.3.1 增加真实GET /catalogs/{catalog_id}/teacher-options及生成方法TeachingService.catalogTeacherOptions。已有目录的负责人可指定本校主教师开班，仍无该班私有数据权限；无catalog_id的旧请求保持本人首班限制。无新模型或迁移。

0.3.2 增加GET /enrollments/mine及TeachingService.myEnrollments，返回当前学生本人的最新选课关系状态和最小班级标签；GET /enrollments/requests保留原字段，追加course_code/course_title/course_archived，生成方法仍为TeachingService.myRequests。历史读取不开放当前课程、名单或管理数据；无模型或迁移变更。字段、筛选、排序及限制见[本人关系交接](../docs/student-relations-handoff.md)。

- [领域不变量](domain-model.md)：已实现对象及后续业务规则。
- 0.4.0实际资料路由涵盖库/提交目标、原始二进制上传、固定版本/定位页段/下载、审核发布和任务；八表迁移为c02d0c00001。Material revision、对象动作和具体目标的review/publication绑定均来自授权投影，不从角色或解析状态推导。接入与验证边界见[资料公共交接](../docs/c02-public-handoff.md)，D1前端和主线接收分别验收。
- 0.4.1为正文/知识点输入检索兼容增量候选：课程库、类型、版本日期筛选及有界命中片段/稳定定位，详见[接口约定](api-conventions.md)。不新增迁移、不改写成功快照；A接收完整SHA后再交D接入。
- [接口约定](api-conventions.md)：鉴权、版本、错误和幂等。
- [后续模块协议](a2-protocols.md)：明确标为设计的内容、考试、关卡、页面和平台能力交接。
- ownership.json：机器读取的角色、分支与路径。
- [集成补丁登记](integration-handoffs.json)：A接收依赖时的具体临时文件范围和原领域责任方；不改变ownership，区别于设计辅助任务。
- [临时辅助任务登记](auxiliary-tasks.json)：设计支线范围、候选及批准/冻结状态；不作为业务身份；现行所有权及A副委托以协作规范和各登记为准，流程见[UI协作](../docs/ui-redesign-coordination.md)。
- [A0 检查与交接](../docs/a0-handoff.md)：运行证据与阶段边界。

领域角色先在自己的目录提交提案：用途、字段、权限、状态、旧新行为、兼容/迁移、依赖及页面注册需求。A 接收可集成实现后，统一发布模型注册、迁移、路由、真实 OpenAPI、SDK 和完整 SHA。消费者合并该基线再依赖新接口；设计协议不进入生成客户端。公共修改中途及时交接。

前端公共入口/HashRouter/路由唯一由 D 维护。B/C 的普通业务页输出独立组件及 PageRegistration 清单，使用 web/src/lib/extensions.ts；C 的关卡编辑器接受 renderPreview，由 D 集成注入。助手例外：C提供内容与生命周期适配器，由D唯一悬浮宿主承载，不注册独立聊天页，见[已批准交接](../docs/assistant-floating-handoff.md)。B 管核心/正式学习与考试，C 管固定内容版本/检索/助手；保持模块单向依赖。
