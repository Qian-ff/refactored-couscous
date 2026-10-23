# D 既有 UI 二次整合：学生班级关系

开工基线 b-ui-integrated 对应提交38fbc9621f97cd2568cbb62b60416ecf3ee8185e（标签对象不是提交SHA）；原D分支codex/d-learning-ui-a2，保留b61626a及全部B/A历史。已核对包含B最终6682ec37a2543e9e50a1bf400a8d70057351c807与A公共foundation修复。执行gpt-6.1-sol/xhigh，未改全局默认。

2026-10-23接续：保留cf3f421与88946176两次WIP，合并A的student-relations-ready=f1de72a89ad2a720b6d0d5fbdf5d027293f9a375；合并提交a682b4951215b471dad9b25a07052791da20bfa8。当前消费真实0.3.2 SDK，接口缺口和pnpm阻塞已解除。D网页与A API分别验证，不把A旧网页或既有客户端当成本批产品证据。

## 设计与修改归属

沿用批准的青#087F8C、辅助蓝#2563EB、工作底#F5F8FA、纸面#FFFFFF、正文#172B3A和包内Noto。使用frontend-design及原公共组件，课程卡保留器材主视觉，申请与历史使用记录簿式标签列表；不添加统计或虚构学习数据。桌面保持现有侧栏和单一工作区，手机折行操作及至少44px触控目标，班级代码局部换行。

D只修改自身routes/styles/components/features/student与测试。B的七条注册、courseId参数、admin/teaching业务文件和ui.tsx/business.css保留。既有注册/资料/改密/公共会话和HashRouter继续使用；助手、题库、考试、培训记录、监控和未来工作台保持未开放。

## 功能映射

| 功能 | 正式入口 | 服务端能力与边界 |
|---|---|---|
| 班级邀请码加入 | 我的课程/班级申请与历史→使用班级邀请码加入 | TeachingService.joinClass；账号注册邀请与班级邀请码分别说明；active与pending_join分开反馈 |
| 退出教学班 | 当前课程卡/本人教学班详情→退出确认 | TeachingService.leaveClass；withdrawn与pending_leave分开；等待退出审批仍在班 |
| 本人申请与结果 | /student/enrollments | TeachingService.myRequests；分页读取本人申请，已批准申请不推断当前关系 |
| 撤销待处理申请 | 本人申请记录→撤销确认 | cancelMyRequest；仅pending显示操作，409后重读实际审批结果 |
| 当前教学班详情 | /student/courses/:courseId | CoursesService.course；退出/移出/归档后真实拒绝，清空旧内容；不读取班级管理接口 |
| 本人退出/移出/归档历史 | /student/enrollments→本人班级关系历史 | TeachingService.myEnrollments；搜索名称/代码，按实际关系和归档筛选，服务端20条分页；仅active且未归档显示当前班级链接，打开仍由服务端重新鉴权 |

写入使用既有Idempotency-Key；学生join/leave/cancel没有revision字段，不能虚构字段。资料及B已有编辑继续遵守其revision。网络不确定结果保留原请求同键重试；会话变更由公共代次取消旧请求。当前班级邀请码只有有效期和轮换，没有次数上限；账号邀请码才有使用次数，界面不得混用。

## 已接收的接口与数据语义

0.3.1的visible_course_query只允许学生active且非归档，申请记录也不能代替本人关系。A在0.3.2增加GET /enrollments/mine，myRequests补course_title/course_code/course_archived；实现、生成SDK与边界见others/docs/student-relations-handoff.md。D消费正式SDK，不修改公共契约或B文件，不调用班级管理接口给学生补数据。

关系视图是每个班级的最新持久状态，不是完整加退班事件流水；重新加入复用原Enrollment ID并更新关系。班名是查询时当前名称，不是历史快照。关系表没有加入/退出时间，页面不显示编造时间，也不借用申请时间。归档独立于active/withdrawn/removed显示，保留active不表示归档班仍可访问。申请没有关系行时显示真实班级标签，但不推断已入班。已批准申请、历史读取和本机缓存均不授予当前课程、资料或名单权限。

## 验证与复现

20项真实浏览器回归通过：d-ui.spec.ts原有11项，以及enrollments.spec.ts新增9项。覆盖账号注册/强制及普通改密/资料revision冲突、三身份与B七条正式路由、撤权及服务切换清会话、同身份查询竞态、中文IME、直接和审批加退班、重复申请/撤销/审批冲突、退出审批取消或拒绝仍在班、重新加入复用关系、失效轮换/过期/跨校代码、真实离线、响应丢失后同键退出重试、旧URL拒绝、移出与归档历史、本人申请及关系20+1分页、筛选竞态、长内容及触控。合成账号/班级由实际API建立，不重置演示库。管理API仅用于测试夹具设置；学生浏览器不请求admin、班级management/members/requests接口。

pnpm check、build:web、UI141文件与助手94文件冻结核对通过。D网页5176与A API8000的SHA/树ID/源码指纹/0.3.2分别由globalSetup核验，browser-services.json保存实际值；新增9场景附实际API来源，均为http://127.0.0.1:8000。没有绕过来源检查；失败网络测试仅对真实响应进行丢弃/延迟或设置浏览器离线，不伪造业务成功。

截图包括1440桌面、390手机首屏/全页、长表单和列表、无权、离线/失败、审批冲突及触控结果；触控套件实际使用hasTouch与tap，新流程检查可见动作命中至少44px。报告存当前树忽略目录others/reports/d-ui-integration/，web-tests.json为完整结果，production.json为生产包独立核验；生产输出带当前源码信息、包内字体与OFL，不从设计目录或外网加载资源。最终源码SHA和证据哈希由该目录delivery.json记录。

```powershell
. ./others/scripts/Use-ProjectEnvironment.ps1
pnpm run check
pnpm run build:web
node others/design/ui-redesign/freeze.cjs --check
node others/design/ui-redesign/assistant-floating-v1/freeze.cjs --check
$env:LABCONNECT_REPORT_STAGE='d-ui-integration'
pnpm --filter @safelab/web exec playwright test tests/d-learning/d-ui.spec.ts tests/d-learning/enrollments.spec.ts
node web/tests/d-learning/production.mjs
```

浏览器测试使用A已发布且来源匹配的8000，Playwright启动/验证本树5176，不通过Open-StudentRelations.cmd把A主树网页冒充D。pnpm11.25由主树项目缓存复用；D未安装/升级公共依赖，不改测试配置。

## 交A/F接收

D本批只交可合并源码、功能映射和上述网页证据。A按本分支最终SHA合并，运行公共及B回归，更新并实测本轮一键入口；A/F从合入后的源码重建并实测Windows/安卓，核对包内SHA/契约及学生新流程、1440/390、原生返回和安全区。实体手机、正式安装器与签名仍需各责任方验证。本树网页通过不表示三端完整既有UI验收，不自动放行C/B2。未推送、不更新云端，只有A明确验收后发布C开工新基线。
