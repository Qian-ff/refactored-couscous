# C1 主线依赖基线与下一阶段交接

2026-10-26，A主接收P2。实际功能源码、运行验证及三端产物均为 `bae3461a0e4cba9f6de8b13d12899a965a66b77b`，契约 `0.5.0`、迁移 `c1d0c000001`。本次交接文档的后续提交不重写这些历史来源；各聊天还须包含A实际通知的最新完整交接SHA。原库、两套共享环境和main API8000/Web5173/控制18767已验证，不以候选8002/18768替代。

## 已满足的输入与保留边界

题库/关卡后台、固定审核发布版本、CSV/XLSX传输、教师预览、B2受控服务和学生安全投影已实现；候选及真实main检查分别见[主线接收](c1-main-reception.md)。学生正式学习任务、课程关系/解锁、作答判分和考试gate尚待B2，题库编辑/学习考试界面尚待D2及B。安全DTO本身不创建授权。

专业60题和六关仍为待审核草稿；本次只发布了明确标注的研发合成验证样例。不得称专业教师审核已完成，不批量seed或自动发布。原生持久保存、Windows可见窗口交互、物理安卓、完整语音/助手、G独立验收和监控仍未因此完成。ECS另已完成[2026-10-26的0.5.0更新](c1-cloud-handoff.md)，实测云端cd1，云样例与下列本机ID分开。

## 本机合成固定样例

下列ID只对应当前本机原主库的研发样例，不是生产配置或客户端硬编码常量。已有账号、班级和历史继续保留；读取仍按真实身份和范围授权。恢复或迁移其他环境时核对实际数据，不假设这些ID已存在。

| 对象 | 固定值 |
| --- | --- |
| 教学班course_id | `e9b2dea4-c4cd-4536-b3fc-0e97148df37c` |
| library_id | `8ea81fd2-b42d-4107-b6d4-bce8ba3fb0af` |
| QuestionVersion | `2363fd53-83a7-4280-b50e-d768330bb87d` |
| 题目发布 | `84cab1ed-61e6-4625-963e-04b0d4876a72` |
| LessonVersion | `ab590c48-21ec-4253-8962-b7fea10362b0` |
| 关卡发布 | `b1bb642c-f5e1-4621-9171-76bf210bcdf8` |
| 题目私有快照SHA256 | `6e81a845e0d22e83ac4d7af872f887c1075a3431c143108b21213f278b942246` |
| 关卡私有快照SHA256 | `c48044af38ca7b13aae1f8364dace0cdb19bb42474936aa01cab807d20b041fa` |

快照哈希是本次受控服务输出的摘要，不是学生答案接口，也不等同于每个版本payload_hash。A已只读核对原主库内两项发布均指向上表版本。原始main-flow.json与不可变清单见A副 `others/reports/c1-public/post-main/p2/`，清单SHA256 `462362f5d1d26d6dd8eb930ab14b681ec9b75e1c1c71ef13d002b7bceaa01927`。

## B2 实际服务入口

- `app.domains.content.questions.assessment.resolve_assessment_questions(db, identity, course_id, version_ids)`：在B2发布事务内解析有权的已发布固定版本，B2保存自己的不可变评分快照。题目停用只阻止新发布，不改写旧考试快照。禁止把私有payload/答案DTO挂成学生HTTP响应或允许学生选择purpose调用。
- `app.domains.content.lessons.assessment.resolve_lesson_publication(db, identity, course_id, version_ids)`：返回B2保存的私有素材/评分/场景快照。不能把整个TeacherLessonPreview或SceneSnapshot回给学生。
- `student_lesson_from_snapshot(db, identity, snapshot)`：B2先校验自己的实际任务、关系及解锁，再传服务端保存的可信快照，过滤当前来源授权并生成StudentLesson；不接收学生任意提交的私有快照。JSON和SVG均须B2实际授权，教师预览路由不是学生读取入口。

真实公共接口/生成类型见 [契约入口](../contracts/README.md)；考试、页面、关卡和账号级AI gate按 [a2-protocols](../contracts/a2-protocols.md)。公共模型注册、迁移、契约与SDK归A，D仍唯一维护前端入口/公共路由。

## 下一责任人与首次启动

按[协作规范](coordination.md)及[完整路线](delivery-workflow.md)，技术依赖现已满足；B2、D2、C2仍是新模块首次手动启动，不因统一恢复、只读交接或本基线文件自动执行。各聊天先保留旧提交，在干净登记分支普通合入A通知的完整SHA；旧任务成果不重做。全新模块首次Plan＋grilling＋max，普通已授权实现/返工回到medium，实际设置须核验。

| 聊天 | 首次启动后的职责 | 交接去向 |
| --- | --- | --- |
| B副1 / B2 | core/learning下学习考试、固定发布/作答/续答/超时判分、进度记录、真实账号级gate；B所属教师/管理页面 | 具体公共需求交A；接口与页面注册交D，gate交C；实际候选交A接收 |
| D副3 / D2 | content题库编辑/关卡互动及学生学习界面，三角色入口/工作台；已有0.5接口先接，学生考试消费B2真实接口 | D唯一入口/路由；与B/C按实际接口到达接续，阶段候选交A |
| C副2 / C2 | AI建题草稿、学校AI设置、问答/历史/引用/语音后端及worker；教师先验，学生辅导等待B2真实gate | 接口/生命周期交D，公共接入交A；不恢复旧C02前端或自行创建独立聊天页 |

A主保持main并接收；A副无新源码写任务，后续具体公共/原生工作另按实际包分派。G尚无登记聊天，不自动新建。B2/D2/C2并行时连A共四个，A副集成按容量串行。普通局部问题自查续办，关键不确定和范围外文件集中交A，避免同文件并行编辑。

本基线首次发布时仅本地Git保存；此后用户直接授权GitHub及原ECS更新，cd1已推送并部署，实际结果见[云端接收](c1-cloud-handoff.md)。未创建/移动checkpoint-2，不代表完整A2验收。本机入口为Open-C1-API.cmd与Open-Materials.cmd，原三端通用入口保留。后续首次启动仍核对A通知的完整main SHA及当前规范，不直接把历史bae产物或云端cd1当成文档HEAD。
