import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { AlertCircle, CheckCircle2, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react"
import { isStaleRequest, message, sessionSnapshot, subscribeSession, type SessionSnapshot } from "../../lib/api"
import type { PageProps } from "../../lib/extensions"
import "./business.css"

export function BusinessPage({ page, title, description, children }: { page: PageProps; title: string; description: string; children: ReactNode }) {
  if (page.session.phase !== "ready" || page.session.user?.id !== page.user.id) {
    return <div className="b1-ui"><Notice>正在确认工作身份，请稍候。</Notice></div>
  }
  if (!["teacher", "administrator"].includes(page.session.workRole ?? "")) {
    return <div className="b1-ui"><Notice kind="error">当前工作身份无权打开教学管理页面。</Notice></div>
  }
  return <main className="b1-ui">
    <header className="b1-page-header"><div><span className="b1-eyebrow"><ShieldCheck size={16} /> 安研通 · 教学协同</span>
      <h1>{title}</h1><p>{description}</p></div>
      <span className="b1-scope">{page.user.school?.name ?? "平台运维"}<br />{page.session.workRole === "teacher" ? "教师工作身份" : "管理员工作身份"}</span>
    </header>{children}
  </main>
}

export function Section({ title, description, actions, children }: { title: string; description?: string; actions?: ReactNode; children: ReactNode }) {
  return <section className="b1-section"><header><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions}</header>{children}</section>
}

export function Notice({ kind = "info", children, retry }: { kind?: "info" | "error" | "success"; children: ReactNode; retry?: () => void }) {
  return <div className={`b1-notice b1-${kind}`} role={kind === "error" ? "alert" : "status"}>
    {kind === "success" ? <CheckCircle2 size={19} /> : <AlertCircle size={19} />}<span>{children}</span>
    {retry && <button type="button" className="b1-button b1-secondary" onClick={retry}><RefreshCw size={16} />重试</button>}
  </div>
}

export function Empty({ children }: { children: ReactNode }) { return <div className="b1-empty">{children}</div> }
export function Loading() { return <div className="b1-loading" role="status"><LoaderCircle size={20} className="b1-spin" />正在读取授权范围内的数据…</div> }
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="b1-field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>
}
export function Badge({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return <span className={`b1-badge ${muted ? "b1-badge-muted" : ""}`}>{children}</span>
}
export function Pager({ offset, count, size = 20, change }: { offset: number; count: number; size?: number; change: (value: number) => void }) {
  return <div className="b1-pager"><span>共 {count} 项 · 第 {Math.floor(offset / size) + 1} 页</span><div className="b1-actions">
    <button type="button" className="b1-button b1-secondary" disabled={offset === 0} onClick={() => change(Math.max(0, offset - size))}>上一页</button>
    <button type="button" className="b1-button b1-secondary" disabled={offset + size >= count} onClick={() => change(offset + size)}>下一页</button>
  </div></div>
}

/** Both the global session generation and same-session query order are checked. */
export function useBusinessQuery<T>(session: SessionSnapshot, load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [revision, setRevision] = useState(0)
  const sequence = useRef(0)
  const reload = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    const current = ++sequence.current
    const generation = session.generation
    const unsubscribe = subscribeSession(value => {
      if (value.generation !== generation || value.phase !== "ready") {
        controller.abort(); setData(null); setError(""); setLoading(false)
      }
    })
    setData(null); setError("")
    if (session.phase !== "ready" || generation !== sessionSnapshot().generation) return () => { controller.abort(); unsubscribe() }
    setLoading(true)
    const valid = () => !controller.signal.aborted && current === sequence.current && sessionSnapshot().generation === generation
    load(controller.signal).then(value => { if (valid()) setData(value) }).catch(reason => {
      if (valid() && !isStaleRequest(reason)) setError(message(reason))
    }).finally(() => { if (valid()) setLoading(false) })
    return () => { controller.abort(); unsubscribe() }
  }, [session.generation, session.phase, load, revision])
  return { data, error, loading, reload }
}

export function useBusinessAction(session: SessionSnapshot) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const busy = useRef(false)
  useEffect(() => subscribeSession(value => {
    if (value.generation !== session.generation || value.phase !== "ready") { setError(""); setSuccess(""); setPending(false) }
  }), [session.generation])
  const run = async <T,>(action: (key: string) => Promise<T>, onSuccess?: (value: T) => void, confirmation = "操作已保存") => {
    if (busy.current || session.phase !== "ready" || sessionSnapshot().generation !== session.generation) return
    busy.current = true; setPending(true); setError(""); setSuccess("")
    const generation = session.generation
    try {
      const result = await action(crypto.randomUUID())
      if (sessionSnapshot().generation === generation && sessionSnapshot().phase === "ready") {
        setSuccess(confirmation); onSuccess?.(result)
        return result
      }
    } catch (reason) {
      if (sessionSnapshot().generation === generation && !isStaleRequest(reason)) setError(message(reason))
    } finally { busy.current = false; if (sessionSnapshot().generation === generation) setPending(false) }
  }
  return { pending, error, success, run, clear: () => { setError(""); setSuccess("") } }
}

export function ActionFeedback({ action }: { action: { error: string; success: string } }) {
  return <>{action.error && <Notice kind="error">{action.error}</Notice>}{action.success && <Notice kind="success">{action.success}</Notice>}</>
}

export function input(form: HTMLFormElement, name: string) { return String(new FormData(form).get(name) ?? "").trim() }
export function nullable(value: string) { return value || null }
export function commandHeaders(key: string) { return { "Idempotency-Key": key } }
export const roleName: Record<string, string> = { student: "学生", teacher: "教师", college_admin: "学院管理员", school_admin: "学校管理员", platform_admin: "平台运维" }
