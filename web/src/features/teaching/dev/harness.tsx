/** B-owned development fixture. Product entry, HashRouter and native adapters belong to D/A/F. */
import { useCallback, useEffect, useState } from "react"
import { createRoot } from "react-dom/client"
import { AuthService, CoursesService } from "../../../client"
import { configureService, confirmSession, logoutSession, message, serviceUrl, sessionSnapshot, setToken, subscribeSession, switchWorkRole, type WorkRole } from "../../../lib/api"
import type { PageProps, PlatformBridge } from "../../../lib/extensions"
import { adminPages } from "../../admin/pages"
import { teachingPages } from "../pages"
import { Badge, Field, input, Loading, Notice, SessionPage, useBusinessQuery } from "../ui"
import "../../../styles/index.css"
import "./harness.css"

const bridge: PlatformBridge = {
  kind: "web", microphonePermission: async () => "unavailable",
  startRecording: async () => { throw new Error("B1 夹具未实现原生录音") },
  stopRecording: async () => { throw new Error("B1 夹具未实现原生录音") },
  cancelRecording: async () => {}, speak: async () => { throw new Error("B1 夹具不提供语音能力") }, stopSpeaking: () => {},
  openCitation: async () => { throw new Error("引用能力等待对应模块") }, downloadMaterial: async () => { throw new Error("资料下载等待C/D接入") },
}
const registrations = [...adminPages, ...teachingPages]
const home = (role?: WorkRole) => role === "administrator" ? "/administration/accounts" : "/teaching/courses"

function FixtureClassList(page: PageProps) {
  const rows = useBusinessQuery(page.session, useCallback(async signal => (await CoursesService.courses({ query: { limit: 100 }, signal })).data, []), page.session.workRole !== "student")
  return <SessionPage page={page}><section className="b1-ui"><h1>教学班组件入口</h1><p>从真实授权列表选择班级；本入口仅用于独立组件验证。</p>
    {rows.loading ? <Loading /> : rows.error ? <Notice kind="error" retry={rows.reload}>{rows.error}</Notice> : <div className="b1-card-grid">{rows.data?.data.map(row => <article className="b1-card" key={row.id}><Badge>{row.code}</Badge><h2>{row.title}</h2><p>{row.teacher_name} · {row.college_name}</p><button type="button" className="b1-button" onClick={() => page.navigate(`${page.session.workRole === "administrator" ? "/administration" : "/teaching"}/classes/${row.id}`)}>管理教学班</button></article>)}</div>}
    {rows.data?.count === 0 && <Notice>当前身份尚未获授权教学班。</Notice>}
  </section></SessionPage>
}

function Fixture() {
  const [session, setSession] = useState(sessionSnapshot())
  const [location, setLocation] = useState("")
  const [feedback, setFeedback] = useState("")
  const [pending, setPending] = useState(false)
  useEffect(() => subscribeSession(setSession), [])
  function navigate(path: string) {
    if (!path.startsWith("/") || path.startsWith("//")) throw new Error("不支持的组件目的地")
    setLocation(path)
  }
  const user = session.user
  if (session.phase !== "ready" || !user) return <div className="b1-ui b1-dev-login">
    <span className="b1-eyebrow">安研通 · B1 独立组件验证</span><h1>连接真实服务</h1>
    <p>本页仅供 B1 开发验收；产品入口与公共路由由 D 接入。</p>
    {feedback && <Notice kind="error">{feedback}</Notice>}
    <form className="b1-form" onSubmit={async event => {
      event.preventDefault(); const form = event.currentTarget; setPending(true); setFeedback("")
      try {
        configureService(input(form, "service"))
        const { data } = await AuthService.login({ body: { school_code: input(form, "school"), username: input(form, "username"), password: String(new FormData(form).get("password") ?? "") } })
        setToken(data.access_token); const confirmed = await confirmSession(); navigate(home(confirmed.active_work_role ?? undefined)); form.reset()
      } catch (error) { setToken(undefined); setFeedback(message(error)) } finally { setPending(false) }
    }}>
      <Field label="服务地址"><input name="service" type="url" required defaultValue={new URLSearchParams(window.location.search).get("api") || serviceUrl()} /></Field>
      <Field label="学校代码"><input name="school" defaultValue="demo-a" required /></Field>
      <Field label="登录账号"><input name="username" required autoComplete="username" /></Field>
      <Field label="登录密码"><input name="password" type="password" required autoComplete="current-password" /></Field>
      <button className="b1-button" disabled={pending}>{pending ? "正在确认…" : "进入组件夹具"}</button>
    </form>
  </div>
  if (user.must_change_password) return <div className="b1-ui b1-dev-login"><h1>首次登录请修改密码</h1><p>这是 D 登录交接接口的独立真实验证，正式登录界面由 D 实现。</p>{feedback && <Notice>{feedback}</Notice>}
    <form className="b1-form" onSubmit={async event => {
      event.preventDefault(); const form = event.currentTarget; setPending(true); setFeedback("")
      try {
        await AuthService.changePassword({ body: { old_password: String(new FormData(form).get("old") ?? ""), new_password: String(new FormData(form).get("new") ?? "") } })
        setToken(undefined); setFeedback("密码已修改，旧会话已撤销，请重新登录")
      } catch (error) { setFeedback(message(error)) } finally { setPending(false) }
    }}><Field label="原临时密码"><input name="old" type="password" required autoComplete="current-password" /></Field><Field label="新密码"><input name="new" type="password" minLength={8} maxLength={256} required autoComplete="new-password" /></Field><button className="b1-button" disabled={pending}>修改密码并重新登录</button></form>
    <button className="b1-button b1-secondary" type="button" onClick={() => { void logoutSession().catch(error => setFeedback(message(error))) }}>退出</button>
  </div>
  const selected = location || home(session.workRole)
  const page: PageProps = { user, session, navigate, platform: bridge, params: {} }
  let body = <FixtureClassList {...page} />
  let routeParams: PageProps["params"] = {}
  const registration = registrations.find(value => {
    const expression = new RegExp("^" + value.path.replace(/:([A-Za-z]+)/g, "([^/]+)") + "$")
    const match = selected.match(expression)
    if (!match || !value.workRoles.includes(session.workRole!)) return false
    const names = Array.from(value.path.matchAll(/:([A-Za-z]+)/g)).map(item => item[1])
    routeParams = Object.fromEntries(names.map((name, index) => [name, decodeURIComponent(match[index + 1])]))
    return true
  })
  if (registration) body = <registration.component {...page} params={routeParams} />
  else if (session.workRole === "student") body = <div className="b1-ui"><Notice>学生身份已由服务端确认。学生学习页面由 D 接入，本 B1 夹具不提供管理员或教师页面。</Notice></div>
  return <div className="b1-dev-shell"><header className="b1-dev-top"><strong>安研通 · B1 组件夹具</strong><span>{user.display_name}</span>
    <label>当前工作身份<select aria-label="当前工作身份" value={session.workRole ?? ""} disabled={pending} onChange={async event => {
      const role = event.target.value as WorkRole; setPending(true); setFeedback("")
      try { await switchWorkRole(role); navigate(home(role)) } catch (error) { setFeedback(message(error)) } finally { setPending(false) }
    }}>{user.available_work_roles.map(role => <option key={role} value={role}>{role === "teacher" ? "教师" : role === "administrator" ? "管理员" : "学生"}</option>)}</select></label>
    <button className="b1-button b1-secondary" onClick={() => { void logoutSession().catch(error => setFeedback(message(error))) }}>退出登录</button>
  </header><nav className="b1-dev-nav" aria-label="B1 组件选择">
    {registrations.filter(value => value.navGroup && value.workRoles.includes(session.workRole!)).map(value => <button key={value.id} type="button" className={`b1-button ${selected === value.path ? "" : "b1-secondary"}`} onClick={() => navigate(value.path)}>{value.title}</button>)}
  </nav>{feedback && <div className="b1-ui"><Notice>{feedback}</Notice></div>}{body}</div>
}

createRoot(document.getElementById("root")!).render(<Fixture />)
