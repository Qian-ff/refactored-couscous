import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react"
import axios from "axios"
import { isStaleRequest, message, sessionSnapshot, subscribeSession, type SessionSnapshot } from "../../lib/api"
import type { PageProps } from "../../lib/extensions"
import { Button, Dialog, Notice as PublicNotice, PageContainer, Pagination, Panel, RecordList, StatePanel } from "../../components/labconnect"
export { Button, Dialog, Field, RecordList, SearchFilters, StatePanel } from "../../components/labconnect"
import "./business.css"

export function SessionPage({ page, children }: { page: PageProps; children: ReactNode }) {
  const current = useSyncExternalStore(subscribeSession, sessionSnapshot)
  if (current.phase !== "ready" || current.generation !== page.session.generation || current.user?.id !== page.user.id) {
    return <div className="b1-ui"><Notice>工作身份已改变，正在重新确认页面。</Notice></div>
  }
  return <div key={`${current.generation}:${current.workRole}`}>{children}</div>
}

export function BusinessPage({ page, title, description, children }: { page: PageProps; title: string; description: string; children: ReactNode }) {
  if (page.session.phase !== "ready" || page.session.user?.id !== page.user.id) return <StatePanel kind="loading" title="正在确认工作身份" />
  if (!["teacher", "administrator"].includes(page.session.workRole ?? "")) return <StatePanel kind="forbidden" description="当前工作身份无权打开教学管理页面。" />
  return <div className="b1-ui"><PageContainer title={title} description={description}>{children}</PageContainer></div>
}

export function Section({ title, description, actions, children }: { title: string; description?: string; actions?: ReactNode; children: ReactNode }) {
  return <Panel title={title} actions={actions}>{description && <p className="b1-description">{description}</p>}{children}</Panel>
}

export const Notice = PublicNotice
export function Empty({ children }: { children: ReactNode }) { return <StatePanel kind="empty" description={typeof children === "string" ? children : undefined} /> }
export function Loading() { return <StatePanel kind="loading" title="正在读取授权范围内的数据…" /> }
export function Badge({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return <span className={`b1-badge ${muted ? "b1-badge-muted" : ""}`}>{children}</span>
}
export function Pager({ offset, count, size = 20, change }: { offset: number; count: number; size?: number; change: (value: number) => void }) {
  return <Pagination total={count} offset={offset} pageSize={size} onChange={change} />
}

const narrowQuery = () => window.matchMedia("(max-width: 700px)")
const narrowSubscribe = (notify: () => void) => { const query = narrowQuery(); query.addEventListener("change", notify); return () => query.removeEventListener("change", notify) }
export function useNarrowRecords() { return useSyncExternalStore(narrowSubscribe, () => narrowQuery().matches, () => false) }

/** Domain column mapping: semantic table on desktop, D RecordList on mobile. */
export function BusinessRecords<T>({ items, itemKey, title, fields, actions, titleLabel = "名称", actionLabel = "操作" }: {
  items: readonly T[]; itemKey: (item: T) => string; title: (item: T) => ReactNode;
  fields: readonly { label: string; value: (item: T) => ReactNode }[]; actions?: (item: T) => ReactNode; titleLabel?: string; actionLabel?: string
}) {
  const narrow = useNarrowRecords()
  if (narrow) return <RecordList items={items} itemKey={itemKey} title={title} fields={fields} actions={actions} />
  return <div className="b1-table-wrap"><table className="b1-table"><thead><tr><th>{titleLabel}</th>{fields.map(field => <th key={field.label}>{field.label}</th>)}{actions && <th>{actionLabel}</th>}</tr></thead>
    <tbody>{items.map(item => <tr key={itemKey(item)}><td>{title(item)}</td>{fields.map(field => <td key={field.label}>{field.value(item)}</td>)}{actions && <td><div className="b1-actions">{actions(item)}</div></td>}</tr>)}</tbody></table></div>
}

/** A business editor consumes D Dialog; unconfirmed local input never persists. */
export function EditorDialog({ title, children, onClose, pending = false, savedVersion }: { title: string; children: ReactNode; onClose: () => void; pending?: boolean; savedVersion?: string | number }) {
  const [dirty, setDirty] = useState(false)
  const [discard, setDiscard] = useState(false)
  useEffect(() => { setDirty(false) }, [savedVersion])
  return <><Dialog title={title} long busy={pending} onClose={() => { if (dirty) setDiscard(true); else onClose() }}>
    <div className="b1-editor-body" onInputCapture={() => setDirty(true)} onChangeCapture={() => setDirty(true)}>{children}</div>
  </Dialog>{discard && <Dialog title="放弃未保存的修改？" onClose={() => setDiscard(false)} busy={pending}><p>当前输入尚未保存。若操作结果尚未确认，请返回原表单先用原请求重试。</p><div className="b1-actions"><Button variant="secondary" onClick={() => setDiscard(false)}>继续编辑</Button><Button variant="danger" onClick={onClose}>放弃并关闭</Button></div></Dialog>}</>
}

/** Both the global session generation and same-session query order are checked. */
export function useBusinessQuery<T>(session: SessionSnapshot, load: (signal: AbortSignal) => Promise<T>, enabled = true) {
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
    setData(null); setError(""); setLoading(false)
    if (!enabled || session.phase !== "ready" || generation !== sessionSnapshot().generation) return () => { controller.abort(); unsubscribe() }
    setLoading(true)
    const valid = () => !controller.signal.aborted && current === sequence.current && sessionSnapshot().generation === generation
    load(controller.signal).then(value => { if (valid()) setData(value) }).catch(reason => {
      if (valid() && !isStaleRequest(reason)) setError(message(reason))
    }).finally(() => { if (valid()) setLoading(false) })
    return () => { controller.abort(); unsubscribe() }
  }, [session.generation, session.phase, load, revision, enabled])
  return { data, error, loading, reload }
}

export function useBusinessAction(session: SessionSnapshot) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const busy = useRef(false)
  const uncertainCommand = useRef<{ signature: string; key: string; generation: number } | undefined>(undefined)
  useEffect(() => subscribeSession(value => {
    if (value.generation !== session.generation || value.phase !== "ready") {
      uncertainCommand.current = undefined; setError(""); setSuccess(""); setPending(false)
    }
  }), [session.generation])
  const run = async <T,>(action: (key: string) => Promise<T>, onSuccess?: (value: T) => void,
    confirmation = "操作已保存", signature?: string) => {
    if (busy.current || session.phase !== "ready" || sessionSnapshot().generation !== session.generation) return
    busy.current = true; setPending(true); setError(""); setSuccess("")
    const generation = session.generation
    const previous = uncertainCommand.current
    const key = signature && previous?.signature === signature && previous.generation === generation ? previous.key : crypto.randomUUID()
    uncertainCommand.current = signature ? { signature, key, generation } : undefined
    try {
      const result = await action(key)
      if (sessionSnapshot().generation === generation && sessionSnapshot().phase === "ready") {
        uncertainCommand.current = undefined
        setSuccess(confirmation); onSuccess?.(result)
        return result
      }
    } catch (reason) {
      if (isStaleRequest(reason) || (axios.isAxiosError(reason) && reason.response
        && reason.response.status >= 400 && reason.response.status < 500)) uncertainCommand.current = undefined
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
export function utcDate(value: string) { return new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`) }
export function formatTime(value: string) { const date = utcDate(value); return Number.isNaN(date.getTime()) ? "时间不可用" : date.toLocaleString("zh-CN", { hour12: false }) }
export function futureLocalDate(days = 1) { const date = new Date(Date.now() + days * 86_400_000); return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16) }
