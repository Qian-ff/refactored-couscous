# B 教师与管理员页面交接：UI-2026.10-v1

消费 A 已发布的 `0.3.1` 真实契约和生成 SDK；组件基线为 `d-ui-components-ready` / `27c1e385d2e0b97ce5880e0230bae2be7aa1a5c1`。D 已挂载下表七条正式 HashRouter 页面，B 在此基础上迁移展示；完整学生加退班整合和原生验收仍待 D/A/F 接续。

## D 接入页面

从 `../admin/pages.ts` 导入 `adminPages`，从 `./pages.ts` 导入 `teachingPages`，目前已由 D 合并到公共 `PageRegistration[]`；路径、params、工作身份和接口保持原样。D 唯一维护入口、HashRouter 和路由权限。不要导入 `dev/harness.tsx`。

| 路径 | 当前工作身份 | 页面 |
| --- | --- | --- |
| `/administration/organizations` | administrator | 学校 / 学院 / 专业管理，按有效授权范围显示 |
| `/administration/accounts` | administrator | 账号查询、开通、资料、授权、重置、CSV |
| `/administration/invitations` | administrator | 学生开通邀请，区别于教学班邀请码 |
| `/administration/courses` | administrator | 课程目录、教学班、负责人和主教师调整 |
| `/administration/classes/:courseId` | administrator | 有范围的班级管理；详情不作导航菜单 |
| `/teaching/courses` | teacher | 课程目录、首班、已有目录开班和授权班级 |
| `/teaching/classes/:courseId` | teacher | 本班设置、名单、审批、协作、交接、归档 |

使用公共 `PageProps`：`user`、`session`、只读 `params`、`navigate`、`platform`。`courseId` 始终为教学班 ID；`catalog_id` 为课程目录 ID，不能混用。详情查询及写入由服务端再次授权；隐藏按钮不能代替授权。

组件复用 `lib/api.ts` 的会话和 SDK，不收 token。页面经 `SessionPage` 在身份代次变化时卸载；查询另用 AbortController 和序号防同身份乱序覆盖。退出、切身份、切服务时不保留原结果或 CSV 原文。命令使用 Idempotency-Key；同会话同载荷的网络失败 / 5xx 保留不确定请求键，重试不重复创建；载荷或身份变化不复用。

`business.css` 只适配 B 领域展示及含 `.b1-editor-body` 的公共 Dialog。公共壳提供一次边距，BusinessPage 消费 PageContainer 提供唯一 main/h1；Section 消费 Panel，字段、按钮、状态、分页和搜索均使用公共导出。桌面语义表格与手机 RecordList 使用同一份列/动作映射；手机筛选可展开，条件不丢失。EditorDialog 消费公共 Dialog，桌面侧置、390 全屏，标题固定、正文滚动；未保存关闭须确认。危险确认只包装原 action.run，未另造请求或幂等机制。

## 登录、首次改密与个人资料交 D

1. `AuthService.login` 使用学校代码、登录账号、密码；学生学号独立保存，不把 username 当学号。登录后调用公共 `setToken`、`confirmSession`，从真实 `available_work_roles` / `active_work_role` 显示工作身份。
2. `must_change_password=true` 时只提供改密 / 退出；业务接口返回 403。使用 `AuthService.changePassword({body:{old_password,new_password}})`，成功后所有旧会话撤销，清本地 token 并要求重新登录。普通账号改密同样撤销全部旧会话。
3. 使用 `switchWorkRole`，等服务端确认后挂载对应页面；不可把标签切换当成工作身份切换。失败保持明确提示，不能保留旧管理员结果。
4. `ManagementService.getProfile` 返回 `AccountView`；`updateProfile` 只接受 revision、gender、contact。学校、学院、专业、姓名、学号由有范围管理员维护。更新带 Idempotency-Key，409 时重新读取，不猜 revision。
5. 学生注册使用 `AuthService.invitationContext` / `registerAccount`。邀请限定学校、学院、专业、有效期和次数；学生填写独立学号和自己设置的密码。无指定专业时选择邀请返回的合法专业。注册不自动登录。
6. 失效登录 401、当前身份禁止 403、范围外资源 404、修订 / 幂等载荷冲突 409、校验失败 422 分别处理。使用公共 `message`，不回显密码或完整请求载荷。服务端停用 / 撤权后旧 token 不保留原权限。

## 独立开发验收

仅在已迁移的本机合成环境运行。依赖复用共享入口，不安装第二套环境。先核对 8001 / 5174 归属；只重启自己启动的进程。测试前的 API 和网页 SHA、源码指纹、工作树、契约均由公共辅助校验。

```powershell
python .\others\scripts\shared_env.py backend uvicorn app.main:app --host 127.0.0.1 --port 8001
# 另一个终端，同一个 B 工作树
pnpm --filter @safelab/web exec playwright test --config src/features/teaching/dev/playwright.config.ts
```

夹具 URL 为 `/src/features/teaching/dev/index.html?api=http%3A%2F%2F127.0.0.1%3A8001`。它只渲染注册组件，复用真实登录和公共会话；没有替代公共产品路由。`dev/` 不应成为发布入口。

证据写入本树忽略的 `others/reports/b-ui/`：`services.json`、`results.json`、hook-preservation.json，以及正式页面 / 独立夹具的 1440、390 PNG；长抽屉另存底部截图。密码、CSV和完整邀请码遮蔽；认证 trace 关闭。输出放在源码目录外，避免报告改变服务源码指纹。测试只创建合成账号和班级，不重置演示库；新建测试班最终归档。

网页构建包含正式入口和这些 B 页面；网页实测不替代 A/F 重新构建 Windows / Android 和原生运行。B1 历史记录仍在 core/handoff/b1-completion.md，本轮 UI 映射、来源与证据见 handoff/b-ui-completion.md。后续顺序保持 B → A集成 → D二次整合学生既有入口 → A/F既有UI验收 → A明确发布C开工基线。

## 公共组件使用与页面衔接

- 公共组件只从 components/labconnect 导入，B 的 ui.tsx 是领域展示适配层。SessionPage / useBusinessQuery / useBusinessAction 与组件基线函数文本一致，原会话、取消、幂等和 revision 行为不变。
- 课程目录与教学班现在各有搜索和分页；保留全部授权班级、目录筛选、当前 / 归档条件。主讲教师、目录所有者是展示术语，现有接口字段 is_primary / owner_id 不改名。
- CSV 从“批量导入账号 / 名单”进入对应公共长弹窗；模板、文件 / 文本、逐行预检、整批提交与原请求重试全部保留。关闭确认后卸载流程，清理敏感内存；未确认结果关闭不会撤销服务器已收到的命令。
- 组织 / 账号编辑保留完整字段、只读编码、角色授权 / 撤销、启停和重置。冲突不覆盖输入，提供明确读取最新入口。转交和归档使用短确认，归档代码只作客户端保护，不追加 API 字段。
- 班级分区导航只滚动到现有面板，不卸载未提交表单。D 后续学生加退班、申请和撤销继续使用现有接口，不能引入第二个业务身份壳或另造班级 ID。
- 助手、考试、题库、记录和监控保持真实未开放状态；D 仍是唯一悬浮助手宿主，后续 C / F / B2 按已批准分工接续。
