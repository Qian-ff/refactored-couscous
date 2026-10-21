import { cloneElement, isValidElement, useEffect, useId, useRef, type ButtonHTMLAttributes, type FormEvent, type ReactElement, type ReactNode } from "react"
import { AlertCircle, BookOpen, CheckCircle2, LoaderCircle, Search, X } from "lucide-react"

export function Button({ variant = "primary", pending = false, children, className = "", disabled, type = "button", ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" | "danger"; pending?: boolean }) {
  return <button {...props} type={type} disabled={disabled || pending} aria-busy={pending || undefined}
    className={`lc-button lc-${variant} ${className}`}>{pending && <LoaderCircle className="lc-spin" size={18} />}{children}</button>
}
export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  const id = useId()
  const control = isValidElement(children) && ["input", "select", "textarea"].includes(String(children.type))
    ? cloneElement(children as ReactElement<{ id?: string; "aria-describedby"?: string; "aria-invalid"?: boolean }>, { id, "aria-describedby": [hint && `${id}-help`, error && `${id}-error`].filter(Boolean).join(" ") || undefined, "aria-invalid": error ? true : undefined }) : children
  return <div className="lc-field"><label htmlFor={id}>{label}</label>{control}{hint && <small id={`${id}-help`}>{hint}</small>}{error && <small id={`${id}-error`} role="alert" className="lc-field-error">{error}</small>}</div>
}
export function Notice({ children, kind = "info", retry }: { children: ReactNode; kind?: "info" | "error" | "success" | "warning"; retry?: () => void }) {
  return <div className={`lc-notice lc-notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
    {kind === "success" ? <CheckCircle2 size={19} /> : <AlertCircle size={19} />}<div>{children}</div>
    {retry && <Button variant="secondary" onClick={retry}>重试</Button>}</div>
}
export function StatePanel({ kind, title, description, retry }: {
  kind: "loading" | "empty" | "error" | "offline" | "forbidden" | "unconfigured" | "unavailable"; title?: string; description?: string; retry?: () => void
}) {
  const names = { loading: "正在读取", empty: "暂无记录", error: "读取失败", offline: "网络已断开", forbidden: "当前身份无权访问", unconfigured: "尚未配置服务", unavailable: "功能尚未开放" }
  return <section className="lc-state" role={kind === "error" || kind === "forbidden" ? "alert" : "status"}>
    {kind === "loading" ? <LoaderCircle className="lc-spin" size={30} /> : <BookOpen size={30} />}<h2>{title || names[kind]}</h2>
    {description && <p>{description}</p>}{retry && <Button variant="secondary" onClick={retry}>重新读取</Button>}</section>
}
/** Shell owns gutters; PageContainer owns the sole main and page heading. */
export function PageContainer({ title, description, actions, children }: { title: string; description?: string; actions?: ReactNode; children: ReactNode }) {
  return <main className="lc-page"><header className="lc-page-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="lc-actions">{actions}</div>}</header>{children}</main>
}
export function Panel({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return <section className="lc-panel">{(title || actions) && <header className="lc-section-heading"><h2>{title}</h2><div className="lc-actions">{actions}</div></header>}{children}</section>
}
export function SearchFilters({ value, onChange, onSearch, onClear, label = "关键词", placeholder, children, pending = false }: {
  value: string; onChange: (value: string) => void; onSearch: () => void; onClear: () => void; label?: string; placeholder?: string; children?: ReactNode; pending?: boolean
}) {
  const composing = useRef(false)
  function submit(event: FormEvent) { event.preventDefault(); if (!composing.current) onSearch() }
  return <form className="lc-search" onSubmit={submit}><Field label={label}>
    <input value={value} placeholder={placeholder} maxLength={100} onChange={e => onChange(e.target.value)}
      onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }}
      onKeyDown={e => { if (e.key === "Enter" && (e.nativeEvent.isComposing || composing.current)) e.preventDefault() }} /></Field>{children}
    <Button type="submit" pending={pending}><Search size={18} aria-hidden />搜索</Button><Button variant="secondary" onClick={onClear}>清空</Button></form>
}
export function Pagination({ total, offset, pageSize, onChange, pending = false }: { total: number; offset: number; pageSize: number; onChange: (offset: number) => void; pending?: boolean }) {
  return <nav className="lc-pagination" aria-label="分页"><span>共 {total} 条{total > 0 && `，第 ${offset + 1}–${Math.min(offset + pageSize, total)} 条`}</span><div className="lc-actions">
    <Button variant="secondary" disabled={pending || offset === 0} onClick={() => onChange(Math.max(0, offset - pageSize))}>上一页</Button>
    <Button variant="secondary" disabled={pending || offset + pageSize >= total} onClick={() => onChange(offset + pageSize)}>下一页</Button></div></nav>
}
export function RecordList<T>({ items, itemKey, title, fields, actions }: { items: readonly T[]; itemKey: (item: T) => string; title: (item: T) => ReactNode;
  fields: readonly { label: string; value: (item: T) => ReactNode }[]; actions?: (item: T) => ReactNode }) {
  return <ul className="lc-records">{items.map(item => <li key={itemKey(item)}><h3>{title(item)}</h3><dl>{fields.map(field => <div key={field.label}><dt>{field.label}</dt><dd>{field.value(item)}</dd></div>)}</dl>{actions && <div className="lc-actions">{actions(item)}</div>}</li>)}</ul>
}
export function Dialog({ title, children, onClose, busy = false, long = false }: { title: string; children: ReactNode; onClose: () => void; busy?: boolean; long?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null), id = useId()
  useEffect(() => { const el = ref.current; const previous = document.activeElement as HTMLElement | null; el?.showModal(); return () => { el?.close(); previous?.focus() } }, [])
  return <dialog ref={ref} className={`lc-dialog ${long ? "lc-dialog-long" : ""}`} aria-labelledby={id} onKeyDown={event => {
    if (event.key !== "Tab") return
    const nodes = [...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')].filter(node => node.getClientRects().length > 0)
    const first = nodes[0], last = nodes[nodes.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }}
    onCancel={e => { e.preventDefault(); if (!busy) onClose() }}><header><h2 id={id}>{title}</h2><Button variant="quiet" aria-label={`关闭${title}`} disabled={busy} onClick={onClose}><X size={20} /></Button></header><div className="lc-dialog-content">{children}</div></dialog>
}
