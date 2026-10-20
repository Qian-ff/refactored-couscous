# 领域对象与数据边界

本文件记录业务不变量，不代替实际数据库迁移。A1 已实现 School、College、User、RoleGrant、Course、CourseStaff、Enrollment、LoginSession；其余领域留待后续模块。

| 对象 | 主要关系与规则 |
|---|---|
| School | 学校租户，所有学校业务数据受其约束 |
| College / Major | 学校内组织；学院管理员可授权多个学院 |
| User / RoleGrant | 学校账号与授权范围；可兼任角色；学号按学校唯一 |
| LoginSession | 保存服务端JWT会话标识与撤销时间；退出后旧令牌失效 |
| Course / CourseStaff | 一名主教师，可协作、交接；课程有归属学院 |
| Enrollment | 学生和课程多对多；加入/退出可按课程审批 |
| Material / MaterialVersion | 授权范围、来源、提取状态及版本 |
| Question / QuestionVersion | 草稿、审核发布与来源；考试引用固定版本 |
| Assignment / Assessment | 课程任务、抽题及分项达标规则 |
| Attempt / Answer | 服务端判分、重复提交幂等、规则和题目快照 |
| LearningProgress | 关卡结果、错题、知识薄弱点；正式进度由服务端保存 |
| TrainingRecord | 自动生成、适用范围、有效期与状态；历史保留 |
| Lab / MonitorNode / Stream | 本地节点和指定区域；监控观看另行授权 |
| AlertEvent / CaseDraft | 疑似、确认/排除、关闭；审核后转去身份教学案例 |
| ProviderProfile | 平台默认及学校覆盖；加密密钥不返回前端 |
| Job / AuditEvent | 长任务、进度、故障、幂等及操作审计 |

跨学院选课只开放该课程所需学生资料和学习记录，不开放外学院全部档案。学生选课不授予监控观看权限。退课、教师交接和课程归档保留历史成绩。

已发布题目、评分规则和试卷保留版本；新版本影响后续任务，既有作答保持可追溯。
