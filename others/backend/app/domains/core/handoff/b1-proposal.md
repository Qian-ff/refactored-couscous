# B1 实现及公共集成提案

角色 B / codex/b-core-a2。准备基线 `1adfe1c70162547a204c9aeb7c7ce4ede8bde1b4`（a2-ready 的 commit；annotated tag 对象不是执行 SHA）。本文件是实现提案，不表示接口已经发布。

## 兼容与分工

复用 CourseCatalog/catalog_id、Course/course_id、工作身份及 app/core/grants.py 的锁定授权写入。旧账号、旧课程 ID 和旧创建请求保留，不重复目录回填迁移。只修改 B 四目录。A 集成迁移、模型注册、公共路由/版本/SDK；D 后续注册页面。后续顺序 B1→C→B2→D→A2。

## 持久对象与迁移请求

| 对象 | 新增内容与状态 |
| --- | --- |
| School / College | is_active，组织停用保留数据；学校停用后学校账号不可访问 |
| Major | 学校、学院、代码、名称、is_active；同校学院代码唯一与组织复合外键 |
| User | student_no（学校内唯一，可空以兼容旧账号）、major_id、gender/contact、must_change_password、revision；新学生必须提供独立学号/专业；旧账号不伪造资料 |
| CourseCatalog | revision / archived；代码、名称、学院、负责人沿用现有字段；已有班级不直接改挂目录 |
| Course | revision / archived、join_approval、leave_approval、邀请码散列与有效期；教学班代码语义不变 |
| CourseStaff | is_active；保留关系历史；活动主教师部分唯一索引（course_id where is_primary AND is_active） |
| EnrollmentRequest | 班级、学生、join/leave、pending/approved/rejected/canceled、处理者和时间；待处理请求唯一保护 |
| AccountInvitation | 学校/学院/可选专业、散列邀请码、到期、使用上限/已用次数、撤销；仅开学生账号，教师/管理员仍上级授权 |
| CoreAuditEvent | 主体/身份/学校、操作、对象、结果摘要、时间；不保存密码、令牌、原始 CSV 或个人联系方式 |
| CommandReceipt | 主体/工作身份/操作/幂等键唯一，HMAC 请求指纹和非敏感结果；同键不同载荷409，不持久化明文密码 |

A 负责实际 Alembic 迁移及新模型集中导出。为现有字段采用保持行为的默认值；学生历史缺少专业/学号继续兼容，在管理界面显示待补。迁移检测多主教师等既有冲突，报告并停止，不能静默删除。现有 role_family_guard 保持有效。

## 公共 API 方案

统一 /api/v1。新增写接口使用 Idempotency-Key；编辑使用 revision，冲突409；旧 /courses 创建不强制增加请求字段。事务内重新加载当前账号/会话/身份/权限，锁定目标账号并复用 add_role_grant。B1 普通写入使用学校级事务 advisory lock，避免批量账号、加退班和交接的跨资源锁顺序竞态；读查询不加该锁。

| 接口组 | 行为 / 字段 |
| --- | --- |
| /auth/me、/profile | 扩展个人资料、must_change_password；/profile 仅本人资料，不接收角色/组织任意变更 |
| /auth/change-password | old_password/new_password；临时密码仅能读取本人/改密/退出，改密撤销全部旧会话并要求重登 |
| /admin/schools、/admin/colleges、/admin/majors | 授权范围列表、创建、编辑/停用；学校开通仅平台运维，学院管理仅本校校管理员 |
| /admin/accounts | 范围查询/创建/详情/编辑/停用；学生资料与账号分开；初始临时密码在请求中提供且强制首改；不返回哈希 |
| /admin/accounts/{id}/grants | 上级授予/撤销角色；禁止自改角色、跨范围及管理更高/同级管理员；学生与教职互斥 |
| /admin/accounts/{id}/reset-password | 显式新临时密码，撤销全部会话；不调用演示重置器 |
| /admin/account-invitations、/auth/register | 学生邀请生成/撤销；公开注册提交学校/邀请码/学生资料/本人密码，验证次数与到期，注册不产生登录令牌 |
| /imports/template、/imports/preview、/imports/commit | CSV 账号/名单模板、逐行预检、原子确认；确认带原始 CSV 和预检摘要再次验证；账号 CSV 不覆盖已有账号，初始密码不在预检/提交结果/日志中回显；名单引用已有学生 |
| /catalogs | 范围检索、详情、创建、编辑/归档；目录负责人不因此获得班级管理/成绩权限 |
| /courses（原路径） | 增加 q/catalog_id/college_id/archived 筛选，数据库授权后计数分页；创建支持可选 catalog_id，旧请求创建目录及首班 |
| /courses/{id}/settings、/staff、/transfer、/archive | 本班配置、协作添加/撤销、原子主教师交接、归档；协作无权授权/交接/归档 |
| /courses/{id}/members、/requests | 本班必要名单、拉入/移出、审批列表与决策；跨学院不开放完整学生档案 |
| /courses/{id}/invite、/enrollments/join、/courses/{id}/leave | 主教师/管理员轮换班级邀请码；学生加入/退出，按班配置审批；重复请求不多建关系 |
| /learning/tutoring-status | B1 只返回 unavailable / B2_NOT_IMPLEMENTED，不能伪造学生可辅导；B2 接续实现账号级真实状态 |
| /learning/training-records | B1 明确503 TRAINING_RECORDS_NOT_IMPLEMENTED；本人历史访问授权服务先交付，正式记录随B2真实对象接入 |

列表 q 长度≤100、offset≥0、limit 1–100，稳定代码/ID排序；先授权、再过滤、count及分页。跨校/越范围详情返回404；普通操作权限403；冲突409；字段问题422；未实现503。面向班级教师的跨学院学生只返回ID、学号、姓名、学院，不含联系方式、密码或其他班级记录。学校级账号目录不开放给教师/学生；拉入通过本校精确账号标识解析最小信息。

## 权限与历史

- 只使用当前工作身份 effective grants。平台运维开学校和校管理员；校管理员管理本校组织、学院管理员/教师/学生；学院管理员管理其范围教师/学生，不能授同级或更高角色。多学院按实际授权合并。
- 教师可新建本人目录及首班；已有目录负责人/有范围管理员开班；跨学院目录与班级组合仅校管理员/平台运维协调。目录负责人仅管理目录及共享资源，不等于所有班主教师。
- 主教师/有范围管理员授权教师、交接和归档；活动协作教师可教学与调本班名单。每班保留唯一活动主教师，交接前后锁班级并校验 revision。
- 待退出审批仍有原访问权限；审批通过、移出/退班后无当前资源权限。归档班只允许原有范围教师/管理员读取历史，不继续开放学生当前资料；学生本人历史培训记录独立于选课有效性。
- 当前班/目录关系、角色撤销和停用逐请求重查。学校停用阻断本校账号；组织停用不删历史，并阻止新的开通/分配。

## 给 C 的授权服务

提交 resource_access 服务，使用服务端资源描述（platform_public/school/college/catalog/course、school_id、college_id、catalog_id、course_id、published、creator_id）判定 read/submit/review，不能把客户端参数作为授权。

公共发布资源可读不授予学校私库；课程共享版本只给该目录下当前有权班级关系（及明确目录管理者）；班级私有、草稿独立校验。目录共享由教师提交、负责人/有范围管理员审核；平台公共写入仅平台管理身份。C 负责版本、答案DTO、实际文件与引用/复制新草稿，不由B伪造内容接口。退出一个班仍有另一合法班时可继续读取目录共享，但不能读取退出班私有资源。

## 页面注册与真实验证

输出教师目录/班级列表及班级管理组件，管理员组织、账号/授权/CSV/邀请及课程调整组件；PageRegistration 复用公共 PageProps/SessionSnapshot，不另建 token。D 后续接入 /teaching/* 与 /administration/*，登录/首改/个人资料交 D。

按 a2-protocols 在 B 目录内建开发渲染夹具与独立 Playwright 配置，复用公共来源检查与真实API；不改公共路由/测试配置，测试1440/390布局及真实创建/变更/失败。页面仅在A真实SDK发布后消费。

测试覆盖真实PG、角色族并发、唯一主教师交接、密码/会话、CSV失败回滚/并发冲突/幂等、双班/跨校/跨院/撤权权限及计数。A0既有回归必须继续通过。B1完成不是B2或A2完成。
