# 学生本人关系接口与 D 接续

2026-10-23，A / main。基于b-ui-integrated（38fbc9621f97cd2568cbb62b60416ecf3ee8185e）补齐D第二批的只读依赖，发布本地student-relations-ready；完整提交用git rev-parse 'student-relations-ready^{}'取得。真实契约0.3.2，迁移仍为b1c0e0a00001，无DDL或演示数据重置。原领域责任方仍为B，A本次两文件补丁登记在[integration-handoffs.json](../contracts/integration-handoffs.json)。

## 接口与生成 SDK

| 接口 | SDK | 数据与限制 |
|---|---|---|
| GET /api/v1/enrollments/mine | TeachingService.myEnrollments | Page_SelfEnrollmentView_；仅当前有效学生本人的真实Enrollment |
| GET /api/v1/enrollments/requests | TeachingService.myRequests | Page_SelfRequestView_；原RequestView字段保留，追加班级标签 |

SelfEnrollmentView字段只有enrollment_id、course_id、course_code、course_title、course_archived、status。status为active/withdrawn/removed，archived独立；不返回其他学生、名单、教师、学院档案或管理资料。q最多100字符，字面匹配代码/名称；status默认all，archived省略为全部；offset默认0、limit默认50且1–100。服务端先限定本人和学校，再筛选、计数，按班级code/id、关系id稳定分页。

SelfRequestView保留id、course_id、user_id、display_name、kind、status、created_at、decided_at，新增course_code、course_title、course_archived。沿用offset/limit及created_at倒序、id排序；这里只返回本人申请。申请不存在关系行时也有安全班级标签，不必调用学生无权访问的management或members。

这份关系视图表示最新持久状态，不是完整加入/退出事件流水。Enrollment没有创建/更新时间；不得显示编造时间、用申请时间冒充加入/退出时间，或把approved申请当作当前在班证明。班级名称是查询时当前名称，不是历史名称快照。历史读取不会改变visible_course_query，不开放已退班、移出或归档班级的当前资源。

## 学生操作语义

现行/courses用于当前可访问班级，本人关系接口用于状态/历史元数据，申请接口用于审批记录。重新加入会复用已有Enrollment ID并更新其状态。各页只按服务端实际结果呈现，无关系行时不能从pending申请推断已在班。

join/leave/cancel使用Idempotency-Key，没有revision输入；有revision的管理操作仍按实际DTO处理。班级邀请码有过期与轮换，没有max_uses。账号注册邀请是另一套入口，才有次数上限。

## D 恢复工作

保留D当前第二批WIP提交，不把WIP当作完成交付或直接并入A。D在登记树/codex/d-learning-ui-a2先合并student-relations-ready的完整提交，再点载others/scripts/Use-ProjectEnvironment.ps1，核对真实0.3.2 SDK与A8000服务身份，恢复[D第二批Goal](ai/D-learning-ui.md)。A不自动合并D树、不自动唤醒聊天。

A的API仍使用127.0.0.1:8000，D网页5176；必须分别核验API归A、网页归D的SHA/树/源码指纹/契约，不绕过旧服务拒绝。本人关系页面及D已有WIP的最终真实浏览器检查由D完成，交A后再完整既有UI与三端验收。C_B2_new_features_allowed与existing_ui_accepted_by_A保持false。

## 环境、入口与检查

pnpm11.25.0已恢复到主树忽略的others/cache/tools/pnpm/11.25.0，Use-ProjectEnvironment.ps1按Git common directory复用，只改当前shell PATH。来源、SHA512及MIT归档见[共享环境](shared-environment.md)和[许可](licensing.md)。A安装入口为python others/scripts/prepare_pnpm.py，离线验证加--check；各树无需独立安装CLI。

Open-StudentRelations.cmd与Open-BUI.cmd均启动现有正式网页和同一API。本次新增的是接口依赖，网页仍为B集成版本；登录学生查看现有课程，不会提前出现D尚未合并的历史页。通用Windows/安卓入口保持可用，客户端重新构建和源码/契约元信息分别记录。

本轮真实PostgreSQL/API回归92项通过，含新增22项本人关系检查；Ruff、网页类型/构建、实际OpenAPI/哈希/生成SDK一致性通过。专用测试库事务与夹具不重置演示库。检查日志、运行来源与产物证据存于忽略的others/reports/student-relations-api/，构建、运行及D页面验收各自记录，不互相替代。

本次仅本地依赖发布，不推送、不更新云端，不移动b-ui-integrated等历史标签。题库、考试、助手、监控、实体手机及正式安装器仍按原阶段交付。
