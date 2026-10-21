import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react"
import { Link, useLocation, useNavigate } from "react-router"
import axios from "axios"
import { FlaskConical, Settings2, ShieldCheck } from "lucide-react"
import { AuthService, ManagementService, type InvitationContextView, type ProfilePatch } from "../../client"
import { configureService, confirmSession, isStaleRequest, logoutSession, message, serviceUrl, sessionSnapshot, setToken } from "../../lib/api"
import { Button, Dialog, Field, Notice, PageContainer, Panel, StatePanel } from "./index"
import { useCommand } from "./hooks"
import labBench from "./assets/illustrations/lab-bench.svg"
import fontLicenseUrl from "./assets/fonts/OFL.txt?url"
import branding from "../../../../others/config/branding.json"

let accountNotice = ""
export function notifyAccount(value: string) { accountNotice = value; window.dispatchEvent(new Event("labconnect-account-notice")) }
export function Brand() { return <div className="lc-brand"><span><FlaskConical size={28} /></span><div><strong>{branding.brandName}</strong><small>{branding.englishName}</small></div></div> }
export function AccountLayout({ children }: { children: ReactNode }) {
  return <div className="lc-account-layout"><aside className="lc-account-story"><Brand /><div><h1>每一次实验，<br />从安全与协作开始。</h1><p>连接学校、教师与学生，让课程归属清晰，<br />让实验室安全学习有序开展。</p><img src={labBench} alt="" /></div><footer>{branding.fullName}<br />{branding.tagline}</footer></aside>
    <main className="lc-account-main"><div className="lc-account-mobile-brand"><Brand /></div><div className="lc-account-card">{children}</div><footer>安研通 · LabConnect <a href={fontLicenseUrl} download="NotoSansSC-OFL.txt">字体许可</a></footer></main></div>
}
export function ServiceSettings({ onClose }: { onClose: () => void }) {
  const [value, setValue] = useState(serviceUrl()), [error, setError] = useState("")
  return <Dialog title="服务连接设置" onClose={onClose}><form className="lc-form" onSubmit={event => {
    event.preventDefault(); try { configureService(value.trim()); notifyAccount("服务连接设置已保存，请登录。"); onClose() } catch (reason) { setError(message(reason)) }
  }}><p>填写学校或平台提供的服务地址。更换地址后需重新登录。</p><Field label="服务地址" hint="此处不填写数据库或 AI 接口密钥。"><input type="url" required value={value} onChange={e => setValue(e.target.value)} placeholder="https://学校提供的服务地址" /></Field>
    {error && <Notice kind="error">{error}</Notice>}<div className="lc-actions"><Button variant="secondary" onClick={onClose}>取消</Button><Button type="submit">保存连接设置</Button></div></form></Dialog>
}
export function AccountEntry({ phase }: { phase: string }) {
  const location = useLocation(), navigate = useNavigate()
  const [notice, setNotice] = useState(() => { const value = accountNotice || (sessionSnapshot().reason === "unauthorized" ? "登录状态已失效，请重新登录。" : ""); accountNotice = ""; return value })
  const [settings, setSettings] = useState(false), [pending, setPending] = useState(false)
  const busy = useRef(false)
  useEffect(() => { const update = () => { setNotice(accountNotice); accountNotice = "" }; window.addEventListener("labconnect-account-notice", update); return () => window.removeEventListener("labconnect-account-notice", update) }, [])
  if (phase === "switching" || phase === "closing") return <AccountLayout><StatePanel kind="loading" title={phase === "switching" ? "正在确认工作身份" : "正在清理登录状态"} /></AccountLayout>
  if (location.pathname === "/register") return <AccountLayout><RegistrationPage />{settings && <ServiceSettings onClose={() => setSettings(false)} />}</AccountLayout>
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy.current) return; busy.current = true; setPending(true); setNotice("")
    const form = new FormData(event.currentTarget)
    try {
      if (!serviceUrl()) throw new Error("请先设置学校提供的服务地址")
      const { data } = await AuthService.login({ body: { school_code: String(form.get("school")).trim(), username: String(form.get("username")).trim(), password: String(form.get("password")) } })
      setToken(data.access_token)
      await confirmSession()
      if (["/login", "/register", "/"].includes(location.pathname)) navigate("/", { replace: true })
    } catch (reason) {
      if (!isStaleRequest(reason)) {
        // The generation change replaces this form; keep the error for the replacement instead of consuming it here.
        accountNotice = message(reason)
        setToken()
      }
    } finally { busy.current = false; setPending(false) }
  }
  return <AccountLayout><div className="lc-kicker"><ShieldCheck size={16} />实验室安全 · 教学协作</div><h2>欢迎使用安研通</h2><p>使用学校分配的账号，开启本次学习与协作。</p>
    {notice && <Notice>{notice}</Notice>}<form className="lc-form" onSubmit={login}>
      <Field label="学校代码"><input name="school" autoComplete="organization" required defaultValue="demo-a" maxLength={40} /></Field>
      <Field label="登录账号" hint="登录账号与学生学号可能不同，请使用开通的账号。"><input name="username" autoComplete="username" required maxLength={80} /></Field>
      <Field label="登录密码"><input name="password" type="password" autoComplete="current-password" required maxLength={256} /></Field>
      <Button className="lc-full" type="submit" pending={pending}>登录</Button></form>
    <div className="lc-account-links"><Link to="/register">使用学生账号邀请注册</Link><Button variant="quiet" onClick={() => setSettings(true)}><Settings2 size={16} />连接设置</Button></div>
    <Notice>账号由学校统一管理。首次登录需修改临时密码；请勿与他人共用账号。</Notice>
    {!serviceUrl() && <StatePanel kind="unconfigured" description="请通过连接设置填写服务地址。" />}
    {settings && <ServiceSettings onClose={() => setSettings(false)} />}</AccountLayout>
}
export const genderOptions = <><option value="unspecified">不填写</option><option value="male">男</option><option value="female">女</option><option value="other">其他</option></>
export type Gender = NonNullable<ProfilePatch["gender"]>
function RegistrationPage() {
  const [context, setContext] = useState<InvitationContextView>(), [invite, setInvite] = useState({ school: "", code: "" })
  const [success, setSuccess] = useState(false), [validation, setValidation] = useState("")
  const action = useCommand()
  if (success) return <><h2>学生账号已开通</h2><Notice kind="success">请使用学校代码、登录账号和本人设置的密码登录。</Notice><p>账号已开通，尚未登录。加入教学班需要登录后使用班级邀请码。</p><Link className="lc-button lc-primary" to="/login">返回登录</Link></>
  return <><div className="lc-kicker"><ShieldCheck size={16} />学生账号邀请</div><h2>开通学生账号</h2><p>学生账号邀请用于注册；班级邀请码用于登录后加入教学班。</p>
    {!context ? <form className="lc-form" onSubmit={async event => {
      event.preventDefault(); const form = new FormData(event.currentTarget)
      const school = String(form.get("school")).trim(), code = String(form.get("invite")).trim()
      const result = await action.run("invitation-context", () => ManagementService.invitationContext({ path: { code }, query: { school_code: school } }))
      if (result) { setInvite({ school, code }); setContext(result.data) }
    }}><Field label="学校代码"><input name="school" required maxLength={40} defaultValue="demo-a" /></Field>
      <Field label="学生账号邀请码"><input name="invite" required minLength={16} maxLength={100} autoComplete="off" /></Field>
      {action.error && <Notice kind="error">{action.error}</Notice>}<Button type="submit" pending={action.pending}>核验邀请</Button></form>
      : <form className="lc-form" onSubmit={async event => {
        event.preventDefault(); setValidation(""); const form = new FormData(event.currentTarget)
        if (form.get("password") !== form.get("confirm")) { setValidation("两次输入的密码不一致"); return }
        const major = String(form.get("major"))
        if (!context.majors.some(item => item.id === major)) { setValidation("请选择邀请允许的专业"); return }
        const body = { school_code: invite.school, invitation_code: invite.code, major_id: major, username: String(form.get("username")).trim(), student_no: String(form.get("student_no")).trim(),
          display_name: String(form.get("name")).trim(), password: String(form.get("password")), gender: String(form.get("gender")) as Gender, contact: String(form.get("contact")).trim() || null }
        const result = await action.run(JSON.stringify(body), key => ManagementService.registerAccount({ body, headers: { "Idempotency-Key": key } }))
        if (result) { event.currentTarget?.reset(); setContext(undefined); setSuccess(true) }
      }}><Notice>邀请有效：{context.school_name} / {context.college_name}。专业仅可选择邀请允许的范围。</Notice>
        <div className="lc-form-grid"><Field label="姓名"><input name="name" required maxLength={80} autoComplete="name" /></Field>
        <Field label="学生学号"><input name="student_no" required maxLength={80} /></Field>
        <Field label="登录账号" hint="英文字母、数字或 _.@-；与学号分别保存。"><input name="username" required maxLength={80} pattern="[A-Za-z0-9_.@\-]+" autoComplete="username" /></Field>
        <Field label="专业"><select name="major" required defaultValue={context.majors.length === 1 ? context.majors[0].id : ""}><option value="" disabled>请选择专业</option>{context.majors.map(major => <option key={major.id} value={major.id}>{major.name}</option>)}</select></Field>
        <Field label="性别（选填）"><select name="gender" defaultValue="unspecified">{genderOptions}</select></Field><Field label="联系方式（选填）"><input name="contact" maxLength={120} autoComplete="tel" /></Field>
        <Field label="设置密码" hint="至少8个字符。"><input name="password" type="password" autoComplete="new-password" minLength={8} maxLength={256} required /></Field>
        <Field label="确认密码"><input name="confirm" type="password" autoComplete="new-password" minLength={8} maxLength={256} required /></Field></div>
        {(validation || action.error) && <Notice kind="error">{validation || action.error}</Notice>}
        <Button type="submit" pending={action.pending} disabled={!context.majors.length}>开通学生账号</Button><Button variant="secondary" disabled={action.pending} onClick={() => { setContext(undefined); action.clear() }}>重新核验邀请</Button></form>}
    <div className="lc-account-links"><Link to="/login">返回登录</Link></div></>
}
export function PasswordPage({ forced = false }: { forced?: boolean }) {
  const action = useCommand(), [validation, setValidation] = useState("")
  const [uncertain, setUncertain] = useState(false)
  const form = <Panel><p>{forced ? "为保护账号安全，请先修改临时密码。完成前仅可修改密码或退出。" : "修改成功后，所有旧会话将撤销，请重新登录。"}</p>
    <form className="lc-form" onSubmit={async event => {
      event.preventDefault(); setValidation(""); const form = new FormData(event.currentTarget)
      if (form.get("new") !== form.get("confirm")) { setValidation("两次输入的新密码不一致"); return }
      const result = await action.run("change-password", async () => {
        try { return await ManagementService.changePassword({ body: { old_password: String(form.get("old")), new_password: String(form.get("new")) } }) }
        catch (reason) { if (axios.isAxiosError(reason) && !reason.response && !isStaleRequest(reason)) setUncertain(true); throw reason }
      })
      if (result) { notifyAccount("密码已修改，旧会话已撤销，请重新登录。"); setToken() }
    }}><Field label="原密码"><input name="old" type="password" autoComplete="current-password" required maxLength={256} /></Field>
      <Field label="新密码" hint="至少8个字符，应与原密码不同。"><input name="new" type="password" autoComplete="new-password" required minLength={8} maxLength={256} /></Field>
      <Field label="确认新密码"><input name="confirm" type="password" autoComplete="new-password" required minLength={8} maxLength={256} /></Field>
      {(validation || action.error) && <Notice kind="error">{validation || action.error}</Notice>}{uncertain && <Notice kind="warning">密码修改结果尚未确认，请退出后重新登录核对。</Notice>}<Button type="submit" pending={action.pending} disabled={uncertain}>修改密码并重新登录</Button>
      {(forced || uncertain) && <Button variant="secondary" disabled={action.pending} onClick={async () => { try { await logoutSession() } catch { notifyAccount("本机已退出；远端注销未确认，请联系管理员撤销旧会话。") } }}>{forced ? "退出登录" : "退出并重新登录"}</Button>}</form></Panel>
  return forced ? <AccountLayout><h2>首次登录，请修改密码</h2>{form}</AccountLayout>
    : <PageContainer title="修改密码" description="使用本人密码保护账号。">{form}</PageContainer>
}
