import { useEffect, useState, type FormEvent } from "react"
import { ArrowRight, BookOpen, ChevronRight, FlaskConical, GraduationCap, LayoutDashboard, LogOut, Plus, RefreshCw, Settings2, ShieldCheck, Sparkles } from "lucide-react"
import { AuthService, CoursesService, type CourseContext, type CoursesPublic, type UserPublic } from "./client"
import { Button } from "./components/ui/button"
import { configureService, message, serviceUrl, setToken } from "./lib/api"
import { navigation, roleNames } from "./routes/navigation"
import branding from "../../others/config/branding.json"

const roleLabel = (user: UserPublic) => [...new Set(user.grants.map(grant => roleNames[grant.role] || grant.role))].join(" / ") || "待授权"

export default function App() {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [address, setAddress] = useState(serviceUrl)
  const [showSettings, setShowSettings] = useState(false)
  const [school, setSchool] = useState("demo-a")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [data, setData] = useState<CoursesPublic>({ data: [], count: 0 })
  const [context, setContext] = useState<CourseContext | null>(null)
  const [creating, setCreating] = useState(false)
  const [notice, setNotice] = useState("")

  useEffect(() => {
    function offline() { setError("网络已断开，恢复连接后请重试；课程数据以服务端为准") }
    window.addEventListener("offline", offline)
    return () => window.removeEventListener("offline", offline)
  }, [])

  async function refresh() {
    const [courses, ctx] = await Promise.all([CoursesService.courses(), CoursesService.context()])
    setData(courses.data)
    setContext(ctx.data)
  }

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("")
    try {
      configureService(address)
      const result = await AuthService.login({ body: { school_code: school.trim(), username: username.trim(), password } })
      setToken(result.data.access_token)
      const me = await AuthService.me()
      await refresh()
      setUser(me.data); setPassword(""); setNotice("")
    } catch (error) { setToken(); setError(message(error)) }
    finally { setBusy(false) }
  }

  async function logout() {
    setBusy(true); setError("")
    try {
      await AuthService.logout()
      setToken(); setUser(null); setData({ data: [], count: 0 }); setContext(null)
    } catch (error) { setError(message(error)) }
    finally { setBusy(false) }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("")
    const form = new FormData(event.currentTarget)
    try {
      await CoursesService.createCourse({ body: { college_id: String(form.get("college")), teacher_id: String(form.get("teacher")), code: String(form.get("code")), title: String(form.get("title")) } })
      await refresh(); setCreating(false); setNotice("课程已保存，授权范围内的账号可同步查看")
    } catch (error) { setError(message(error)) }
    finally { setBusy(false) }
  }

  const errorBox = error && <div className="feedback error" role="alert">{error}<button onClick={() => setError("")} aria-label="关闭提示">×</button></div>

  if (!user) return <div className="login-layout">
    <section className="login-story">
      <a className="brand" href="#"><span className="brand-icon"><FlaskConical /></span><span>{branding.brandName}<span className="brand-caption">{branding.englishName}</span></span></a>
      <div className="story-content"><span className="eyebrow"><ShieldCheck size={17} />{branding.fullName}</span>
        <h1>{branding.tagline}</h1>
        <p>连接教师与学生，让每一门安全课程<br className="desktop-only" />都有清晰的学习入口。</p>
        <div className="lab-illustration" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="lab-tile"><FlaskConical size={82} strokeWidth={1.3} /><span>先知风险 · 再行实验</span></div><div className="float-badge badge-one"><ShieldCheck /> 安全从学习开始</div><div className="float-badge badge-two"><GraduationCap /> 教与学，同步连接</div></div>
      </div><small>{branding.fullName}</small>
    </section>
    <main className="login-main"><div className="login-card">
      <span className="pill">欢迎回来</span><h2>登录平台</h2><p className="muted">使用学校账号，进入你的安全学习空间。</p>
      {errorBox}
      <form onSubmit={login} className="form-stack">
        <label>学校代码<input name="school" autoComplete="organization" value={school} onChange={event => setSchool(event.target.value)} required placeholder="请输入学校代码" /></label>
        <label>账号<input name="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required placeholder="学号或教职工账号" /></label>
        <label>密码<input name="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required placeholder="请输入密码" /></label>
        <Button className="primary-button" disabled={busy || !address} type="submit">{busy ? "正在连接…" : "登录学习空间"}<ArrowRight size={17} /></Button>
      </form>
      <button className="text-button service-toggle" onClick={() => setShowSettings(!showSettings)}><Settings2 size={15} />服务连接设置</button>
      {(showSettings || !address) && <label className="service-field">服务地址<input aria-label="服务地址" type="url" value={address} onChange={event => setAddress(event.target.value)} placeholder="https://你的服务地址" /><small>由学校或平台管理员提供，不填写数据库或 AI 接口密钥。</small></label>}
      <div className="login-note"><ShieldCheck size={18} /><span>账号权限由学校统一管理。<br />首次使用请联系课程教师或管理员。</span></div>
    </div><small className="stage-note">A1 基础版本 · 已开放账号与课程入口</small></main>
  </div>

  return <div className="app-layout">
    <aside className="sidebar"><div className="brand"><span className="brand-icon"><FlaskConical /></span><span>{branding.brandName}<span className="brand-caption">{branding.englishName}</span></span></div>
      <div className="school-label">{user.school?.name || "平台运维空间"}</div>
      <nav aria-label="主导航"><span className="nav-caption">学习与教学</span>{navigation.map((item, index) => <button key={item.key} disabled={!item.available} className={item.available ? "nav-item active" : "nav-item"}><span>{index === 0 ? <BookOpen size={19} /> : index === 1 ? <ShieldCheck size={19} /> : index === 2 ? <Sparkles size={19} /> : <GraduationCap size={19} />}{item.label}</span>{!item.available && <small>筹备中</small>}</button>)}</nav>
      <div className="sidebar-footer"><ShieldCheck /><strong>先知风险，再行实验</strong><span>从一门安全课程开始</span></div>
    </aside>
    <div className="main-area"><header className="topbar"><div><span className="breadcrumb">工作台</span><ChevronRight size={14} /><strong>我的课程</strong></div><div className="profile"><span className="avatar">{user.display_name.slice(0, 1)}</span><span><strong>{user.display_name}</strong><small>{roleLabel(user)}</small></span><button onClick={logout} disabled={busy} aria-label="退出登录" title="退出登录"><LogOut size={18} /></button></div></header>
      <main className="workspace"><div className="page-heading"><div><span className="eyebrow"><LayoutDashboard size={15} /> 课程工作台</span><h1>每一次实验，都从安全开始</h1><p className="muted">查看你有权访问的课程，连接接下来的学习与教学。</p></div><span className="scope-badge"><ShieldCheck size={16} />{user.college?.name || "按账号授权范围"}</span></div>
        {errorBox}{notice && <div className="feedback success" role="status">{notice}</div>}
        <section className="welcome-banner"><div><span className="eyebrow">欢迎，{user.display_name}</span><h2>你的安全学习空间已就绪</h2><p>课程数据来自学校统一服务，三端同步。</p><div className="banner-tags"><span>统一账号</span><span>按课程授权</span><span>服务端保存</span></div></div><div className="banner-mark" aria-hidden="true"><ShieldCheck size={112} strokeWidth={1.1} /></div></section>
        <div className="summary-grid"><div><span className="stat-icon"><BookOpen /></span><p>可访问课程<strong data-testid="course-count">{data.count}<small> 门</small></strong></p></div><div><span className="stat-icon blue"><GraduationCap /></span><p>当前身份<strong className="stat-role">{roleLabel(user)}</strong></p></div><div><span className="stat-icon mint"><ShieldCheck /></span><p>数据范围<strong className="stat-role">{user.school ? "本校授权资源" : "平台运维授权"}</strong></p></div></div>
        <section className="course-section"><div className="section-heading"><div><h2>我的课程</h2><span>仅展示当前账号有权访问的内容</span></div><div className="actions"><button className="refresh-button" aria-label="刷新课程" disabled={busy} onClick={async () => { setBusy(true); setError(""); try { await refresh() } catch (error) { setError(message(error)) } finally { setBusy(false) } }}><RefreshCw size={16} /></button>{context?.can_create && <Button className="create-button" onClick={() => setCreating(true)}><Plus size={17} />新建课程</Button>}</div></div>
          {data.data.length ? <div className="course-grid">{data.data.map((course, index) => <article className="course-card" key={course.id}><div className={`course-cover cover-${index % 3}`}><FlaskConical size={50} strokeWidth={1.3} /><span>实验室安全 · 基础课程</span><small>{course.code}</small></div><div className="course-body"><span className="course-category">{course.college_name}</span><h3>{course.title}</h3><div className="course-meta"><span className="teacher-avatar">{course.teacher_name.slice(0, 1)}</span>{course.teacher_name}<span className="course-state">课程已建立</span></div><div className="course-foot"><span>学习内容待教师发布</span><span className="pill subtle">A1 课程入口</span></div></div></article>)}</div> : <div className="empty-state"><BookOpen size={40} /><h3>暂时没有可访问的课程</h3><p>请联系教师加入课程；有管理权限时可新建课程。</p></div>}
        </section><div className="foundation-note"><ShieldCheck size={17} />已开放账号、授权与基础课程。关卡、考核、助手和培训记录将在后续阶段接入。</div>
      </main><footer>{branding.tagline}</footer></div>
    {creating && context && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="create-title" className="modal"><div className="section-heading"><h2 id="create-title">新建课程</h2><button onClick={() => setCreating(false)} aria-label="关闭新建课程">×</button></div>{errorBox}<form onSubmit={create} className="form-stack"><label>所属学院<select name="college" required>{context.colleges.map(college => <option key={college.id} value={college.id}>{college.name}</option>)}</select></label><label>主教师<select name="teacher" required>{context.teachers.map(teacher => <option key={teacher.id} value={teacher.id}>{teacher.name}</option>)}</select></label><label>课程代码<input name="code" required maxLength={40} pattern="[A-Za-z0-9_-]+" placeholder="例如 LAB-SAFE-01" /></label><label>课程名称<input name="title" required maxLength={120} placeholder="请输入课程名称" /></label><Button disabled={busy} type="submit" className="primary-button">{busy ? "正在保存…" : "保存课程"}</Button></form></section></div>}
  </div>
}
