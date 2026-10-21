# B1 教师与管理员页面交接

消费 A 已发布的 `0.3.1` 真实契约和生成 SDK。页面组件已在本树独立开发夹具中连接真实 API 验证；产品公共路由、三角色工作台和原生包仍由 D/A 接入。

## D 接入页面

从 `../admin/pages.ts` 导入 `adminPages`，从 `./pages.ts` 导入 `teachingPages`，合并到公共 `PageRegistration[]`。D 唯一维护入口、HashRouter 和路由权限。不要导入 `dev/harness.tsx`。

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

`business.css` 仅使用 `.b1-*`，蓝绿配色，390 宽度改为单列；表格在自身容器内横向滚动，不撑开整页。后续 D 可统一视觉系统，保留现有加载、空、失败重试、无权限、归档只读及功能未开放反馈。

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

证据写入本树忽略的 `others/reports/b1-components/`：`services.json`、`results.json`、失败 trace、组织 / 账号 / 首次改密 / 课程 / 班级 / 邀请的 1440、390 PNG。输出放在源码目录外，避免报告改变服务源码指纹。测试只创建合成账号和班级，不重置演示库；新建测试班最终归档。

现有网页构建验证兼容性和类型；公共产品入口尚未挂载这些页面，不能据此声称 B1 页面已进入正式三端包。最终证据与提交对应关系见后端 `core/handoff/b1-completion.md`。
