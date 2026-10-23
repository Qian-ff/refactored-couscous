# D 既有 UI 二次整合：学生班级关系

开工基线 b-ui-integrated 对应提交38fbc9621f97cd2568cbb62b60416ecf3ee8185e（标签对象不是提交SHA）；原D分支codex/d-learning-ui-a2，保留b61626a及全部B/A历史。已核对包含B最终6682ec37a2543e9e50a1bf400a8d70057351c807与A公共foundation修复。执行gpt-6.1-sol/xhigh，未改全局默认。

## 设计与修改归属

沿用批准的青#087F8C、辅助蓝#2563EB、工作底#F5F8FA、纸面#FFFFFF、正文#172B3A和包内Noto。使用frontend-design及原公共组件，课程卡保留器材主视觉，申请与历史使用记录簿式标签列表；不添加统计或虚构学习数据。桌面保持现有侧栏和单一工作区，手机折行操作及至少44px触控目标，班级代码局部换行。

D只修改自身routes/styles/components/features/student与测试。B的七条注册、courseId参数、admin/teaching业务文件和ui.tsx/business.css保留。既有注册/资料/改密/公共会话和HashRouter继续使用；助手、题库、考试、培训记录、监控和未来工作台保持未开放。

## 功能映射（最终实测状态随交付补充）

| 功能 | 正式入口 | 服务端能力与边界 |
|---|---|---|
| 班级邀请码加入 | 我的课程/班级申请与历史→使用班级邀请码加入 | TeachingService.joinClass；账号注册邀请与班级邀请码分别说明；active与pending_join分开反馈 |
| 退出教学班 | 当前课程卡/本人教学班详情→退出确认 | TeachingService.leaveClass；withdrawn与pending_leave分开；等待退出审批仍在班 |
| 本人申请与结果 | /student/enrollments | TeachingService.myRequests；分页读取本人申请，已批准申请不推断当前关系 |
| 撤销待处理申请 | 本人申请记录→撤销确认 | cancelMyRequest；仅pending显示操作，409后重读实际审批结果 |
| 当前教学班详情 | /student/courses/:courseId | CoursesService.course；退出/移出/归档后真实拒绝，清空旧内容；不读取班级管理接口 |
| 本人退出/移出/归档历史 | 同一申请与历史工作页 | 当前0.3.1缺少真实自助查询，已交A协调，不用申请或本机缓存伪造 |

写入使用既有Idempotency-Key；学生join/leave/cancel没有revision字段，不能虚构字段。资料及B已有编辑继续遵守其revision。网络不确定结果保留原请求同键重试；会话变更由公共代次取消旧请求。当前班级邀请码只有有效期和轮换，没有次数上限；账号邀请码才有使用次数，界面不得混用。

## 已交A的最小接口缺口

0.3.1的visible_course_query只允许学生active且非归档，archived=true仍受此约束；/enrollments/requests只含申请，直接加退班和管理移出不保证有申请。管理members/management不是学生读取入口。

需要真实的本人关系只读分页查询，严格当前student/学校/本人：教学班必要元信息、Enrollment实际active/withdrawn/removed、班级archived。申请中但未建立Enrollment时提供申请所属教学班的安全名称/代码。历史不恢复当前课程、资料或名单访问权；关系表没有加入/退出时间，不能补造时间。具体路由/字段、公共SDK和版本由A发布，D消费已发布基线。

## 检查进度

当前直接调用项目内锁定TypeScript通过，原UI及悬浮助手冻结核对通过。新真实接口套件覆盖直接/审批加退班、重复请求、撤销/并发处理、旧直链、移出/归档/撤权、失效轮换/过期/跨校代码、离线、同键恢复和长列表；运行等待A稳定的公共接口基线。

真实测试来源检查已经正确拒绝A当前编辑中的API源码/契约不匹配，没有关闭检查或用占位数据过关。最终统一记录D网页与A API各自SHA/树/指纹、实际浏览器API来源、1440/390及触控截图。

本轮新会话pnpm启动器缺失，已交A恢复锁定工具；Node24.14及根node_modules现有TS/Vite/Playwright可用。D未安装/升级公共依赖，不改测试配置或其他工作树。当前文件为过程记录，不表示二次整合完成；最终交付更新实际结果与剩余事项，交A/F重建并验收后才由A放行C。
