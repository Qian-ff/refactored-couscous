# 网页页面与已有功能映射（候选v1）

版本：UI-2026.10-v1。所有页面为设计稿、合成数据；用户未批准。现有独立组件随D正式接入，不把本图册当作产品验收。

| 设计稿 | 身份 | 保留功能 | 现有来源 |
| --- | --- | --- | --- |
| [登录](images/login.png) | 公共入口 | 学校、账号、密码；连接设置；登录失败反馈 | web/src/App.tsx |
| [登录失败反馈](images/login-error.png) | 公共入口 | 保留学校与账号输入、错误提示、不泄露账号是否存在 | web/src/App.tsx |
| [服务连接设置](images/service-settings.png) | 公共入口 | 服务地址修改、保存前校验、返回登录 | web/src/App.tsx |
| [首次修改密码](images/first-password.png) | 公共入口 | 临时密码、8–256位规则、必须改密、重新登录 | web/src/features/teaching/dev/harness.tsx |
| [我的课程](images/student-courses.png) | 学生 | 授权课程、搜索、刷新、待开放学习入口 | web/src/App.tsx |
| [课程与教学班](images/teacher-courses.png) | 教师 | 课程目录、新建课程、已有目录开班、范围搜索 | web/src/features/teaching/CoursesPage.tsx |
| [历史教学班](images/courses-history.png) | 教师 | 已归档筛选、恢复在用目录、历史班级独立权限 | web/src/features/teaching/CoursesPage.tsx |
| [课程管理](images/admin-courses.png) | 学院管理员 | 目录归属、编辑、归档、开班、目录权限与班级权限区分 | web/src/features/teaching/CoursesPage.tsx |
| [学校管理](images/organizations-school.png) | 平台运维 | 学校新增、编辑、搜索、启停 | web/src/features/admin/OrganizationsPage.tsx |
| [学院管理](images/organizations-college.png) | 学校管理员 | 本校学院新增、编辑、搜索、启停 | web/src/features/admin/OrganizationsPage.tsx |
| [专业管理](images/organizations-major.png) | 学院管理员 | 授权学院内专业新增、编辑、搜索、启停 | web/src/features/admin/OrganizationsPage.tsx |
| [账号与授权](images/accounts.png) | 学院管理员 | 搜索筛选、新建、编辑、密码重置、批量导入 | web/src/features/admin/AccountsPage.tsx |
| [新建学生账号](images/account-new-student.png) | 学院管理员 | 独立账号与学号、学院专业、可选资料、学生身份互斥 | web/src/features/admin/forms.tsx |
| [编辑学生账号](images/account-edit-student.png) | 学院管理员 | 账号只读、保留学号专业、资料编辑、状态与重置入口 | web/src/features/admin/forms.tsx |
| [新建教职账号](images/account-new-teacher.png) | 学校管理员 | 教师兼管理员、可选专业学号、初始临时密码 | web/src/features/admin/forms.tsx |
| [教师身份与授权](images/account-edit-teacher.png) | 学校管理员 | 教师兼管理员、学院范围、启停、保留账号标识 | web/src/features/admin/forms.tsx |
| [重置密码确认](images/account-reset.png) | 学院管理员 | 临时密码、撤销全部会话、首次强制改密 | web/src/features/admin/AccountsPage.tsx |
| [新增角色授权](images/account-grant.png) | 学校管理员 | 授权角色、学院范围、撤销授权、重新判权 | web/src/features/admin/AccountsPage.tsx |
| [停用账号确认](images/account-status.png) | 学院管理员 | 撤销会话、主讲需先交接、停用与重新启用 | web/src/features/admin/AccountsPage.tsx |
| [学生账号邀请](images/invitations.png) | 学院管理员 | 专业范围、有效期、使用次数、创建、撤销 | web/src/features/admin/InvitationsPage.tsx |
| [新邀请凭据](images/invite-issued.png) | 学院管理员 | 新建时一次展示邀请码；列表不回显明文 | web/src/features/admin/InvitationsPage.tsx |
| [教学班概览](images/class-overview.png) | 主讲教师 | 归属信息、设置、邀请码、转交、归档 | web/src/features/teaching/ClassManagementPage.tsx |
| [学生名单](images/class-roster.png) | 主讲教师 | 搜索、拉入、移出、批量导入、成员状态 | web/src/features/teaching/ClassManagementPage.tsx |
| [加入与退出审批](images/class-requests.png) | 协作教师 | 待审请求、同意、拒绝、请求状态 | web/src/features/teaching/ClassManagementPage.tsx |
| [教师协作](images/class-staff.png) | 主讲教师 | 加入协作教师、移除、主讲区别、授权范围 | web/src/features/teaching/ClassManagementPage.tsx |
| [协作教师视角](images/class-collaborator.png) | 协作教师 | 名单与审批可操作；关键设置、教师管理、转交归档受限 | web/src/features/teaching/ClassManagementPage.tsx |
| [协作教师查看关系](images/class-staff-readonly.png) | 协作教师 | 可查看历史教师关系；无增加、移除、恢复与转交操作 | web/src/features/teaching/ClassManagementPage.tsx |
| [管理员班级视角](images/class-admin.png) | 学院管理员 | 范围授权、班级管理、管理员不冒充教师 | web/src/features/teaching/ClassManagementPage.tsx |
| [已归档教学班](images/class-archived.png) | 主讲教师 | 归档只读、保留历史、停止加入和修改 | web/src/features/teaching/ClassManagementPage.tsx |
| [班级名称与审批设置](images/class-edit.png) | 主讲教师 | 班级名称、加入审批、退出审批、修订校验 | web/src/features/teaching/ClassManagementPage.tsx |
| [拉入学生](images/class-add-member.png) | 主讲教师 | 精确本校学生登录账号、无其他学院学生目录 | web/src/features/teaching/ClassManagementPage.tsx |
| [添加协作教师](images/class-add-staff.png) | 主讲教师 | 本校教师搜索、最小候选资料、明确选择与授课范围 | web/src/features/teaching/ClassManagementPage.tsx |
| [生成班级邀请码](images/class-joincode.png) | 主讲教师 | 有效期、生成新凭据、旧码失效、仅本次明文 | web/src/features/teaching/ClassManagementPage.tsx |
| [转交主讲教师](images/class-transfer.png) | 主讲教师 | 同校候选教师、影响提示、二次确认 | web/src/features/teaching/ClassManagementPage.tsx |
| [归档确认](images/class-archive.png) | 主讲教师 | 归档影响、明确对象与确认 | web/src/features/teaching/ClassManagementPage.tsx |
| [CSV内容编辑](images/csv-input.png) | 学院管理员 | 文件与文本编辑、模板、文件限制、修改后重做预检 | web/src/features/teaching/CsvImporter.tsx |
| [CSV班级名单编辑](images/csv-input-roster.png) | 主讲教师 | 固定班级、文件读取、原始文本编辑、预检 | web/src/features/teaching/CsvImporter.tsx |
| [CSV预检通过](images/csv-preview.png) | 学院管理员 | 模板、文件限制、全量预检、原子提交 | web/src/features/teaching/CsvImporter.tsx |
| [批量加入班级](images/csv-roster.png) | 主讲教师 | 班级固定范围、引用已开通学生、全量预检、原子提交 | web/src/features/teaching/CsvImporter.tsx |
| [CSV预检错误](images/csv-errors.png) | 学院管理员 | 定位行与字段、错误全览、禁止部分写入 | web/src/features/teaching/CsvImporter.tsx |
| [提交结果待确认](images/csv-uncertain.png) | 学院管理员 | 响应丢失、保留原请求、同一幂等键重试 | web/src/features/teaching/CsvImporter.tsx |
| [教师新建课程](images/new-course-teacher.png) | 教师 | 目录与首班一起创建、首班本人主讲、学院范围 | web/src/App.tsx; web/src/features/teaching/CoursesPage.tsx |
| [管理员新建课程](images/new-course-admin.png) | 学校管理员 | 学院与教师选择、目录与首班创建、权限校验 | web/src/App.tsx; web/src/features/teaching/CoursesPage.tsx |
| [已有课程目录开班](images/existing-catalog-new-class.png) | 课程目录所有者 | 可指定同校其他主讲、开班后不默认获得该班访问权 | web/src/features/teaching/CoursesPage.tsx |
| [编辑课程目录](images/edit-catalog.png) | 学院管理员 | 编码只读、标题、所有者、修订版本、归档与恢复 | web/src/features/teaching/CoursesPage.tsx |
| [编辑与停用组织](images/organization-edit.png) | 学校管理员 | 不可变所属学校、组织名称、启停影响 | web/src/features/admin/OrganizationsPage.tsx |
| [编辑与停用学校](images/organization-edit-school.png) | 平台运维 | 学校编码只读、名称、停用后的全校访问影响 | web/src/features/admin/OrganizationsPage.tsx |
| [编辑与停用专业](images/organization-edit-major.png) | 学院管理员 | 学校学院归属只读、名称、状态、历史保留 | web/src/features/admin/OrganizationsPage.tsx |
| [新建组织](images/organization-new.png) | 平台运维 | 编码、名称、组织层级与范围 | web/src/features/admin/OrganizationsPage.tsx |
| [新建学院](images/organization-new-college.png) | 学校管理员 | 学校范围、编码、名称 | web/src/features/admin/forms.tsx |
| [新建专业](images/organization-new-major.png) | 学院管理员 | 学校与学院范围、编码、名称 | web/src/features/admin/forms.tsx |
| [切换已授权身份](images/role-switch.png) | 教师兼学院管理员 | 只显示已有授权身份、缩小权限范围、学生无角色切换 | web/src/features/admin/scope.ts; web/src/features/teaching/dev/harness.tsx |
| [状态样式总览](images/states-sheet.png) | 状态规范草案 | 加载、空、失败重试、离线、无权限、修订冲突、未配置、未开放 | web/src/App.tsx; web/src/features/teaching/ui.tsx |
