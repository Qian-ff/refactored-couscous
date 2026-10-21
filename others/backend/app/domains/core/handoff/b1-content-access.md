# B1 → C / B2 授权交接

本文说明实际领域服务；公共接口、迁移及真实 SDK 已由 A 发布于 `ffeca27e516e53b0caa1a53dca4715d4f170fb48`（0.3.1）。B1 后续权限修正、页面和最终提交见 `b1-completion.md`，接续者须合并 A 最终集成基线。学生考试门控仍未实现，不应从示范账号或页面存在推断可用。

## 请求身份

复用`CurrentIdentity`，不得从客户端用户/角色/学校字段构造Identity。它逐请求验证账号、学校、会话、工作身份和临时密码。`identity.grants`仅含当前工作身份；不要把`all_grants`用于业务授权。

## 搜索先授权

`core.resource_query.ResourceColumns`接收服务端资源表的实际字段：scope/school_id/college_id/catalog_id/course_id/published/creator_id/audience。不存在的父级用SQL `literal(None)`，UUID列保持UUID类型。将`read_resource_predicate(identity, columns)`同时应用于count、分页、定位片段、建议词和后续检索，不先返回所有结果再Python过滤。

scope取`platform_public`/`school`/`college`/`catalog`/`course`，audience取`all`/`staff`。题库管理路径使用staff；学生作答只读C/B2定义的学生DTO，不因为资源可读就返回答案。平台公共条目不得同时携带私有学校/父级ID。

## 详情、下载、审核二次核验

`core.policy.resource_access(db, identity, ResourceDescriptor(...))`返回read/submit/review。描述必须由C读取真实持久资源及固定版本生成，不能直接接受客户端的published或scope。C仍需检查具体审核版本、文件、来源、云处理授权和安全SVG等内容不变量。

- 同校学校私库不开放跨校；平台公共库不成为私库的通道。
- 目录共享只给该目录内当前合法班级关系及明确管理者；负责人不自动获得兄弟班级的名单/私有资料/成绩。
- 教师可提交目录共享，负责人/有范围管理员审核；草稿只给管理者或有权提交的创建者。
- 班级私有发布资料仅该班关系可读；有效任课教师可教学审核，学生无审核权限。
- 退班/移除协作后再次查询关系；仍在同目录另一合法班时，保留共享访问，不保留退出班私有访问。
- `visible_course_query`/`visible_catalog_query`提供领域列表范围。归档班只读教师历史，不给学生当前资源；`may_read_own_training_history`单独表达本人历史访问，B2接真实记录后复用。

C负责引用固定发布版本、复制新草稿、原始答案与学生DTO分离。这里提供授权决策，不提供虚构的文件或题目版本。

## B2 仍未实现

`learning.availability.tutoring_status(student_id)`返回`unavailable`、as_of、`B2_EXAM_STATE_NOT_IMPLEMENTED`，没有HTTP占位或SDK成功声明。C对学生按不可核实暂停处理；教师可按当前工作身份完成C阶段验收。之后B2接入账号级真实状态，覆盖跨班/设备/会话、旧对话及任务结果竞态，依a2-protocols联合验证。

正式培训记录、考试时限/续答/判分/公布也留B2，不以空列表假装已实现。

## 合成示范

`core.demo_b1.seed_b1_examples`显式建立同目录化学/工程双班、独立主教师和只选化学班的工程学生。只用于development/test，不启动时自动执行，不覆盖既有密码。B 已在 A 0.3.1 迁移完成的合成演示库显式运行；共用原演示组织，不下载资料或创建环境。真实共享课件/题目须待C审核发布后再验收。

- 目录：`718f1362-e74e-5d91-90e2-68b98b0ee290`，负责人为原示范 `teacher`。
- 化学班：`7a450989-ad66-5423-9587-f453b04daa6b`，主教师 `teacher`。
- 工程班：`a6000881-622a-58aa-bbff-bdd5e764aeb2`，主教师 `teacher_eng`。
- 跨学院学生：`b1_student_cross`，工程专业，独立学号 `B1-20260001`，只加入化学班。初始合成密码从原忽略配置读取，本文不保存。
- 重复执行时保持现有密码、主教师关系和 Enrollment ID，不恢复使用者已调整的关系。真实 PostgreSQL 用例已覆盖重复运行及原密码不覆盖。
