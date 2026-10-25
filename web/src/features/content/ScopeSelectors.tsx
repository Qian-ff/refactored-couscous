import { useCallback, useRef, useState } from "react"
import { ContentService, CoursesService, type LibraryView } from "../../client"
import { Button, Dialog, Field, Pagination, RecordList, SearchFilters, StatePanel } from "../../components/labconnect"
import { useResource } from "../../components/labconnect/hooks"

export function SubmitTargetChooser({ value, label, onChange, disabled = false, fieldLabel = "提交范围" }: {
  value: string; label?: string; onChange: (id: string, label: string) => void; disabled?: boolean; fieldLabel?: string
}) {
  const [input, setInput] = useState(""), [q, setQ] = useState(""), [offset, setOffset] = useState(0)
  const composing = useRef(false)
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.submitTargets({ query: { q, offset, limit: 20 }, signal })).data, [q, offset]))
  const search = () => { setQ(input.trim()); setOffset(0) }
  return <div className="lc-scope-picker"><Field label="查找可提交范围"><input value={input} maxLength={100} disabled={disabled} onChange={e => setInput(e.target.value)} onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); if (!composing.current && !e.nativeEvent.isComposing) search() } }} /></Field>
    <div className="lc-actions"><Button variant="secondary" onClick={search} disabled={disabled}>查找提交范围</Button><Button variant="secondary" disabled={disabled} onClick={() => { setInput(""); setQ(""); setOffset(0) }}>清空范围查找</Button></div>
    <Field label={fieldLabel}><select value={value} onChange={e => onChange(e.target.value, e.target.selectedOptions[0]?.text || "")} required disabled={disabled || resource.loading}>
      <option value="">请选择获准提交的范围</option>{value && !resource.data?.some(row => row.id === value) && <option value={value}>{label || "当前已选范围"}</option>}{resource.data?.map(row => <option key={row.id} value={row.id}>{row.title}</option>)}
    </select></Field>
    {resource.error && <StatePanel kind="error" description={resource.error} retry={resource.reload} />}
    {!resource.loading && !resource.error && resource.data?.length === 0 && <p>本页没有匹配的可提交范围，可调整关键词或返回上一页。</p>}
    <div className="lc-actions"><span>范围候选第 {offset / 20 + 1} 页</span><Button variant="secondary" disabled={disabled || resource.loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>上页提交范围</Button><Button variant="secondary" disabled={disabled || resource.loading || resource.data?.length !== 20} onClick={() => setOffset(offset + 20)}>下页提交范围</Button></div>
  </div>
}

export function LibraryBrowser({ includeInactive, onChoose, onEdit, onClose }: {
  includeInactive: boolean; onChoose?: (library: LibraryView) => void; onEdit?: (library: LibraryView) => void; onClose: () => void
}) {
  const [input, setInput] = useState(""), [q, setQ] = useState(""), [offset, setOffset] = useState(0)
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.listLibraries({ query: { q, offset, limit: 20, include_inactive: includeInactive }, signal })).data, [q, offset, includeInactive]))
  return <Dialog title={onChoose ? "查找授权资料范围" : "资料库查询与管理"} long onClose={onClose}>
    <SearchFilters value={input} onChange={setInput} label="查找资料库" placeholder="资料库名称" onSearch={() => { setQ(input.trim()); setOffset(0) }} onClear={() => { setInput(""); setQ(""); setOffset(0) }} />
    {resource.loading ? <StatePanel kind="loading" /> : resource.error ? <StatePanel kind="error" description={resource.error} retry={resource.reload} /> : resource.data && <>
      {resource.data.items.length ? <RecordList items={resource.data.items} itemKey={row => row.id} title={row => row.title} fields={[{ label: "范围", value: row => row.scope }, { label: "库状态", value: row => row.active ? "启用" : "停用" }]}
        actions={row => <>{onChoose && row.active && <Button variant="secondary" onClick={() => onChoose(row)}>选择此资料范围</Button>}{onEdit && row.can_manage && <Button variant="secondary" onClick={() => onEdit(row)}>修改资料库</Button>}</>} /> : <StatePanel kind="empty" title="本页没有匹配资料库" />}
      <Pagination total={resource.data.total} offset={offset} pageSize={20} onChange={setOffset} /></>}
    <Button variant="secondary" onClick={onClose}>关闭范围查询</Button>
  </Dialog>
}

export function CourseSelector({ value, label, onChange }: { value: string; label: string; onChange: (id: string, label: string) => void }) {
  const [input, setInput] = useState(""), [q, setQ] = useState(""), [offset, setOffset] = useState(0)
  const composing = useRef(false)
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await CoursesService.courses({ query: { q, offset, limit: 20 }, signal })).data, [q, offset]))
  const search = () => { setQ(input.trim()); setOffset(0) }
  return <div className="lc-course-filter"><Field label="查找课程班级"><input value={input} maxLength={100} onChange={e => setInput(e.target.value)} onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); if (!composing.current && !e.nativeEvent.isComposing) search() } }} /></Field>
    <Button variant="secondary" onClick={search}>查找课程候选</Button>
    <Field label="课程班级筛选"><select value={value} disabled={resource.loading} onChange={e => onChange(e.target.value, e.target.selectedOptions[0]?.text || "")}><option value="">全部有权课程</option>{value && !resource.data?.data.some(row => row.id === value) && <option value={value}>{label}</option>}{resource.data?.data.map(row => <option key={row.id} value={row.id}>{row.code} · {row.title}</option>)}</select></Field>
    {resource.error && <StatePanel kind="error" description={resource.error} retry={resource.reload} />}
    {resource.data && <Pagination total={resource.data.count} offset={offset} pageSize={20} onChange={setOffset} />}
  </div>
}
