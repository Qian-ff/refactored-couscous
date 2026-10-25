import { useEffect, useState } from "react"
import axios from "axios"
import { Link, Navigate, NavLink, Route, Routes, matchPath, useLocation, useNavigate, useParams } from "react-router"
import { BookOpen, ChevronRight, GraduationCap, LogOut, Menu, Settings2, ShieldCheck, Sparkles, UserRound } from "lucide-react"
import { confirmSession, isStaleRequest, logoutSession, message, setToken, switchWorkRole, type SessionSnapshot, type WorkRole } from "../lib/api"
import type { PageProps, PageRegistration, PlatformBridge } from "../lib/extensions"
import { adminPages } from "../features/admin/pages"
import { teachingPages } from "../features/teaching/pages"
import { ProfilePage } from "../features/student/ProfilePage"
import { StudentCoursesPage } from "../features/student/StudentCoursesPage"
import { EnrollmentRequestsPage } from "../features/student/EnrollmentRequestsPage"
import { StudentClassPage } from "../features/student/StudentClassPage"
import { contentPages } from "../features/content/ContentPage"
import { Brand, notifyAccount, PasswordPage, ServiceSettings } from "../components/labconnect/AccountEntry"
import { Button, Dialog, Notice, StatePanel } from "../components/labconnect"

export const productPages: readonly PageRegistration[] = [
  ...adminPages, ...teachingPages, ...contentPages,
  { id: "d-student-courses", path: "/student/courses", title: "我的课程", workRoles: ["student"], component: StudentCoursesPage, navGroup: "courses" },
  { id: "d-student-enrollments", path: "/student/enrollments", title: "班级申请与历史", workRoles: ["student"], component: EnrollmentRequestsPage, navGroup: "courses" },
  { id: "d-student-class", path: "/student/courses/:courseId", title: "教学班", workRoles: ["student"], component: StudentClassPage },
  { id: "d-profile", path: "/account/profile", title: "本人资料", workRoles: ["student", "teacher", "administrator"], component: ProfilePage },
  { id: "d-password", path: "/account/password", title: "修改密码", workRoles: ["student", "teacher", "administrator"], component: () => <PasswordPage /> },
]
const roleNames: Record<WorkRole, string> = { student: "学生", teacher: "教师", administrator: "管理员" }
function home(role?: WorkRole) { return role === "teacher" ? "/teaching/courses" : role === "administrator" ? "/administration/courses" : "/student/courses" }
const unopened = async () => { throw new Error("此设备能力尚未开放，请等待对应功能接入") }
const platform: PlatformBridge = {
  kind: /Electron/i.test(navigator.userAgent) ? "windows" : /Android/i.test(navigator.userAgent) ? "android" : "web",
  microphonePermission: async () => "unavailable", startRecording: unopened, stopRecording: unopened,
  cancelRecording: unopened, speak: unopened, stopSpeaking: () => {}, openCitation: unopened, downloadMaterial: unopened,
}
function RegisteredPage({ registration, session }: { registration: PageRegistration; session: SessionSnapshot }) {
  const params = useParams(), navigate = useNavigate()
  if (!session.user || !session.workRole || !registration.workRoles.includes(session.workRole)) return <StatePanel kind="forbidden" description="请从当前身份的导航进入有权页面。" />
  const Component = registration.component
  const props: PageProps = { user: session.user, session, params, navigate, platform }
  return <div className={registration.id.startsWith("b1-") ? "lc-business-slot" : undefined}><Component {...props} /></div>
}
export function ApplicationShell({ session }: { session: SessionSnapshot }) {
  const location = useLocation(), navigate = useNavigate()
  const [menu, setMenu] = useState(false), [switcher, setSwitcher] = useState(false), [settings, setSettings] = useState(false)
  const [offline, setOffline] = useState(!navigator.onLine), [verified, setVerified] = useState("")
  const [validationError, setValidationError] = useState(""), [validationRound, setValidationRound] = useState(0)
  const role = session.workRole, user = session.user!
  const active = productPages.find(page => matchPath(page.path, location.pathname))
  // Confirm revoked/default identities before mounting a new route and whenever the app regains focus.
  useEffect(() => {
    let current = true
    async function validate() {
      setVerified("")
      setValidationError("")
      try { await confirmSession(); if (current) setVerified(location.pathname) }
      catch (reason) {
        if (current && !isStaleRequest(reason)) {
          if (axios.isAxiosError(reason) && [401, 403].includes(reason.response?.status || 0)) {
            notifyAccount("工作身份或登录状态已失效，请重新登录。"); setToken()
          } else setValidationError(message(reason))
        }
      }
    }
    void validate()
    const focus = () => { void validate() }, offline = () => setOffline(true), online = () => setOffline(false)
    window.addEventListener("focus", focus); window.addEventListener("offline", offline); window.addEventListener("online", online)
    return () => { current = false; window.removeEventListener("focus", focus); window.removeEventListener("offline", offline); window.removeEventListener("online", online) }
  }, [location.pathname, session.generation, validationRound])
  useEffect(() => { setMenu(false); document.title = "安研通"; window.scrollTo(0, 0) }, [location.pathname])
  const navigation = <><div className="lc-scope"><strong>{user.school?.name || "平台运维空间"}</strong><span>{role ? roleNames[role] : "待授权"}工作空间</span></div>
    <nav className="lc-nav" aria-label="正式导航">{productPages.filter(page => page.navGroup && page.workRoles.includes(role!)).map(page => <NavLink key={page.id} to={page.path} onClick={() => setMenu(false)}><BookOpen size={19} />{page.title}</NavLink>)}
      <button disabled><ShieldCheck size={19} />安全学习<small>未开放</small></button><button disabled><Sparkles size={19} />学习助手<small>未开放</small></button>
      <button disabled><GraduationCap size={19} />培训记录<small>未开放</small></button>{role !== "student" && <button disabled><ShieldCheck size={19} />监控预警<small>未开放</small></button>}
      <NavLink to="/account/profile" onClick={() => setMenu(false)}><UserRound size={19} />本人资料</NavLink></nav>
    <div className="lc-sidebar-note"><ShieldCheck size={20} /><strong>让安全管理更智能</strong><span>让实验协同更畅通。</span></div></>
  async function logout() {
    try { await logoutSession() } catch { notifyAccount("本机已退出；远端注销未确认，请联系管理员撤销旧会话。") }
  }
  if (!role) return <StatePanel kind="forbidden" description="账号尚无可用工作身份，请联系学校管理员。" />
  return <div className="lc-app"><a className="lc-skip" href="#lc-workspace" onClick={event => { event.preventDefault(); document.getElementById("lc-workspace")?.focus() }}>跳到主要内容</a><aside className="lc-sidebar"><Brand />{navigation}</aside>
    <div className="lc-main-area"><header className="lc-topbar"><div className="lc-breadcrumb"><Button className="lc-mobile-menu" variant="quiet" aria-label="打开导航菜单" onClick={() => setMenu(true)}><Menu size={22} /></Button><span className="lc-school">{user.school?.name || "平台运维"}</span><ChevronRight className="lc-desktop" size={16} /><strong>{active?.title || "工作空间"}</strong></div>
      <div className="lc-account-tools">{user.available_work_roles.length > 1
        ? <Button variant="secondary" onClick={() => setSwitcher(true)} aria-label="切换工作身份">{roleNames[role]}<span aria-hidden>⌄</span></Button>
        : <span className="lc-role-label">{roleNames[role]}</span>}
        <Link className="lc-profile-link" to="/account/profile"><span className="lc-avatar">{user.display_name.slice(0, 1)}</span><span><strong>{user.display_name}</strong><small>{user.username}</small></span></Link>
        <Button variant="quiet" aria-label="服务连接设置" title="服务连接设置" onClick={() => setSettings(true)}><Settings2 size={18} /></Button>
        <Button variant="quiet" aria-label="退出登录" title="退出登录" onClick={logout}><LogOut size={19} /></Button></div></header>
      <div id="lc-workspace" className="lc-workspace" tabIndex={-1}>{offline && <Notice kind="warning">网络已断开。请恢复连接后重试，尚未确认的操作不能视为成功。</Notice>}
        {validationError ? <StatePanel kind="error" description={validationError} retry={() => setValidationRound(x => x + 1)} /> : verified !== location.pathname ? <StatePanel kind="loading" title="正在确认工作身份" /> : <Routes>
          <Route path="/" element={<Navigate to={home(role)} replace />} /><Route path="/login" element={<Navigate to={home(role)} replace />} /><Route path="/register" element={<Navigate to={home(role)} replace />} />
          {productPages.map(page => <Route key={page.id} path={page.path} element={<RegisteredPage registration={page} session={session} />} />)}
          <Route path="*" element={<main><StatePanel kind="unavailable" title="页面不存在" description="请返回当前身份的工作空间。" /><Link className="lc-button lc-secondary" to={home(role)}>返回工作空间</Link></main>} />
        </Routes>}
      </div><footer className="lc-app-footer">仅显示当前身份可访问的内容 · 安研通 LabConnect</footer></div>
    {role === "student" && <nav className="lc-student-bottom" aria-label="学生快捷导航"><NavLink to="/student/courses"><BookOpen size={20} />课程</NavLink>
      <button disabled><ShieldCheck size={20} /><span>安全学习</span><small>未开放</small></button><button disabled><Sparkles size={20} /><span>学习助手</span><small>未开放</small></button>
      <button disabled><GraduationCap size={20} /><span>培训记录</span><small>未开放</small></button></nav>}
    {menu && <Dialog title="导航菜单" long onClose={() => setMenu(false)}><div className="lc-mobile-nav">{navigation}</div><Button variant="secondary" onClick={logout}>退出登录</Button></Dialog>}
    {switcher && <Dialog title="切换工作身份" onClose={() => setSwitcher(false)}><p>切换后将按服务端确认的身份重新读取授权范围。</p><div className="lc-identity-options">{user.available_work_roles.map(value => <Button key={value} variant={value === role ? "primary" : "secondary"} onClick={async () => {
      setSwitcher(false)
      try { await switchWorkRole(value); navigate(home(value), { replace: true }) } catch (reason) { if (!isStaleRequest(reason)) notifyAccount(message(reason)) }
    }}>{roleNames[value]}{value === role && "（当前）"}</Button>)}</div></Dialog>}
    {settings && <ServiceSettings onClose={() => setSettings(false)} />}
  </div>
}
