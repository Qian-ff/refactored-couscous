import { useCallback, useState } from "react"
import { ContentService, CoursesService, TeachingService, type UserPublic, type LibraryCreate as LibraryInput } from "../../client"
import { Button, Dialog, Field, Notice, Pagination, SearchFilters, StatePanel } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"

export function LibraryCreate({ user, onClose, onDone }: { user: UserPublic; onClose: () => void; onDone: (message: string) => void }) {
  const [scope, setScope] = useState<LibraryInput["scope"]>("course"), [parent, setParent] = useState(""), [title, setTitle] = useState("")
  const [audience, setAudience] = useState<"staff" | "all">("staff"), [input, setInput] = useState(""), [q, setQ] = useState(""), [offset, setOffset] = useState(0)
  const grants = user.effective_grants.map(grant => grant.role), action = useCommand()
  const resources = useResource(useCallback(async (signal: AbortSignal) => {
    if (scope === "platform_public") return { items: [] as { id: string; label: string }[], total: 0 }
    if (scope === "school") return { items: user.school ? [{ id: user.school.id, label: user.school.name }] : [], total: user.school ? 1 : 0 }
    if (scope === "college") { const result = (await CoursesService.context({ signal })).data; return { items: result.colleges.map(row => ({ id: row.id, label: row.name })), total: result.colleges.length } }
    if (scope === "catalog") { const result = (await TeachingService.catalogs({ query: { q, offset, limit: 20 }, signal })).data; return { items: result.data.map(row => ({ id: row.id, label: row.title })), total: result.count } }
    const result = (await CoursesService.courses({ query: { q, offset, limit: 20 }, signal })).data
    return { items: result.data.map(row => ({ id: row.id, label: row.title })), total: result.count }
  }, [scope, q, offset, user.school]))
  return <Dialog title="新建资料库" long busy={action.pending} onClose={onClose}>
    <Notice>从当前可浏览范围选择归属，服务端在创建时核验审核管理权；可提交资料不代表可新建库。面向学生的资料仍须逐版本审核发布。</Notice>
    <Field label="库范围"><select value={scope} onChange={e => { setScope(e.target.value as typeof scope); setParent(""); setOffset(0); setQ(""); setInput("") }} disabled={action.pending}>
      <option value="course">教学班</option><option value="catalog">课程目录</option>{grants.some(role => ["college_admin", "school_admin", "platform_admin"].includes(role)) && <option value="college">学院</option>}{grants.some(role => ["school_admin", "platform_admin"].includes(role)) && user.school && <option value="school">本校</option>}{grants.includes("platform_admin") && <option value="platform_public">平台公共</option>}
    </select></Field>
    {["course", "catalog"].includes(scope) && <SearchFilters value={input} onChange={setInput} label="查找归属范围" placeholder="代码或名称" onSearch={() => { setQ(input.trim()); setOffset(0); setParent("") }} onClear={() => { setInput(""); setQ(""); setOffset(0); setParent("") }} />}
    {resources.loading ? <StatePanel kind="loading" /> : resources.error ? <StatePanel kind="error" description={resources.error} retry={resources.reload} /> : <form className="lc-form" onSubmit={async e => {
      e.preventDefault(); if (!title.trim()) return
      const body: LibraryInput = { title: title.trim(), scope, parent_id: scope === "platform_public" ? null : parent, audience }
      const result = await action.run(JSON.stringify(body), key => ContentService.createLibrary({ body, headers: { "Idempotency-Key": key } }))
      if (result) onDone("服务端已确认创建资料库。新库中的资料尚未发布。")
    }}>{scope !== "platform_public" && <Field label="归属对象"><select value={parent} onChange={e => setParent(e.target.value)} required disabled={action.pending}><option value="">请选择获准管理的对象</option>{resources.data?.items.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></Field>}
      {["course", "catalog"].includes(scope) && <Pagination offset={offset} total={resources.data?.total || 0} pageSize={20} onChange={value => { setOffset(value); setParent("") }} />}
      <Field label="资料库名称"><input value={title} onChange={e => setTitle(e.target.value)} required maxLength={200} disabled={action.pending} /></Field>
      <Field label="发布阅读对象"><select value={audience} onChange={e => setAudience(e.target.value as typeof audience)} disabled={action.pending}><option value="staff">教职人员</option><option value="all">包含有权学生</option></select></Field>
      {action.error && <Notice kind="error">{action.error}</Notice>}<div className="lc-actions"><Button variant="secondary" onClick={onClose} disabled={action.pending}>取消新建</Button><Button type="submit" pending={action.pending}>创建资料库</Button></div>
    </form>}
  </Dialog>
}
