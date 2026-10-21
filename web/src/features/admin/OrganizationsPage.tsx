import { useCallback, useState } from "react"
import { ManagementService, type OrganizationInput, type OrganizationView } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { FilterFields, ConfirmCommand, type ConfirmationCommand, EditorDialog, SearchFilters, BusinessRecords, Button, ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, input, Loading, Notice, Pager, Section, SessionPage, useBusinessAction, useBusinessQuery } from "../teaching/ui"
import { Options, OrganizationForm } from "./forms"
import { isPlatform, isSchoolManager, useOrganizationChoices } from "./scope"

export function OrganizationsPage(page: PageProps) { return <SessionPage page={page}><OrganizationsBody {...page} /></SessionPage> }
function OrganizationsBody(page: PageProps) {
  const kinds = isPlatform(page) ? ["school", "college", "major"] as const : isSchoolManager(page) ? ["college", "major"] as const : ["major"] as const
  const [kind, setKind] = useState<"school" | "college" | "major">(kinds[0])
  const [term, setTerm] = useState("")
  const [creating, setCreating] = useState(false)
  const [q, setQ] = useState("")
  const [offset, setOffset] = useState(0)
  const [editing, setEditing] = useState<OrganizationView | null>(null)
  const choices = useOrganizationChoices(page)
  const [confirmation, setConfirmation] = useState<ConfirmationCommand | null>(null)
  const action = useBusinessAction(page.session)
  const rows = useBusinessQuery(page.session, useCallback(async signal => {
    if (kind === "school") return (await ManagementService.listSchools({ query: { q, offset, limit: 20 }, signal })).data
    if (kind === "college") return (await ManagementService.listColleges({ query: { q, school_id: choices.schoolId, offset, limit: 20 }, signal })).data
    return (await ManagementService.listMajors({ query: { q, college_id: choices.collegeId || undefined, offset, limit: 20 }, signal })).data
  }, [kind, q, offset, choices.schoolId, choices.collegeId]), page.session.workRole === "administrator"
    && (kind === "school" || Boolean(choices.schoolId && (kind === "college" || choices.collegeId))))
  function refresh() { rows.reload(); choices.reload() }
  function create(form: HTMLFormElement) {
    const body: OrganizationInput = { code: input(form, "code"), name: input(form, "name"), ...(kind !== "school" ? { school_id: choices.schoolId } : {}), ...(kind === "major" ? { college_id: choices.collegeId } : {}) }
    void action.run(async key => {
      const options = { body, headers: commandHeaders(key) }
      return (await (kind === "school" ? ManagementService.createSchool(options) : kind === "college" ? ManagementService.createCollege(options) : ManagementService.createMajor(options))).data
    }, () => { form.reset(); setCreating(false); refresh() }, "组织已创建", JSON.stringify(["organization-create", kind, body]))
  }
  const names = { school: "学校", college: "学院", major: "专业" }
  if (page.session.workRole !== "administrator") return <div className="b1-ui"><Notice kind="error">请使用管理员工作身份。</Notice></div>
  return <BusinessPage page={page} title="组织管理" description="维护学校、学院和专业，按当前授权范围操作，保留历史数据。">
    {!creating && !editing && <ActionFeedback action={action} />}
    {(choices.schools.error || choices.colleges.error || choices.majors.error) && <Notice kind="error" retry={choices.reload}>{choices.schools.error || choices.colleges.error || choices.majors.error}</Notice>}
    <div className="b1-tabs">{kinds.map(value => <Button key={value} type="button" variant={kind === value ? "primary" : "secondary"} onClick={() => { setKind(value); setOffset(0); setEditing(null) }}>{names[value]}管理</Button>)}</div>
    <Section title={`${names[kind]}列表`} description="停用保留历史；学校停用后，本校账号不能继续访问。" actions={<Button onClick={() => { setCreating(true); action.clear() }}>新建{names[kind]}</Button>}>
      <SearchFilters label="搜索名称或代码" value={term} onChange={setTerm} onSearch={() => { setQ(term.trim()); setOffset(0) }} onClear={() => { setTerm(""); setQ(""); setOffset(0); rows.reload() }}><FilterFields>
        {kind !== "school" && <Field label="学校"><select value={choices.schoolId} onChange={event => { choices.selectSchool(event.target.value); setOffset(0); setEditing(null) }}><Options values={choices.schools.data?.data ?? []} /></select></Field>}
        {kind === "major" && <Field label="学院"><select value={choices.collegeId} onChange={event => { choices.selectCollege(event.target.value); setOffset(0); setEditing(null) }}><Options values={choices.colleges.data?.data ?? []} /></select></Field>}
      </FilterFields></SearchFilters>
      {rows.loading ? <Loading /> : rows.error ? <Notice kind="error" retry={rows.reload}>{rows.error}</Notice> : rows.data?.count === 0 ? <Empty>当前范围内没有匹配的{names[kind]}。</Empty> : rows.data && <>
        <BusinessRecords items={rows.data.data} itemKey={row => String(row.id)} titleLabel="名称" title={row => <>{row.name}</>} fields={[{ label: "代码", value: row => <>{row.code}</> }, { label: "状态", value: row => <><Badge muted={!row.is_active}>{row.is_active ? "启用" : "停用"}</Badge></> }]} actionLabel="管理" actions={row => <><Button type="button" variant="secondary" onClick={() => setEditing(row)}>编辑{names[kind]}</Button></>} />
        <Pager offset={offset} count={rows.data.count} change={setOffset} />
      </>}
    </Section>
    {editing && <EditorDialog title={`编辑${names[kind]}：${editing.name}`} pending={action.pending} savedVersion={editing.revision} onClose={() => setEditing(null)}>
      <ActionFeedback action={action} /><Field label="代码（只读）"><input value={editing.code} readOnly /></Field>
      <form className="b1-form" key={`${editing.id}:${editing.revision}`} onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body = { revision: editing.revision, name: input(form, "name"), is_active: input(form, "is_active") === "true" }
        const path = { record_id: editing.id }
        editing.is_active && !body.is_active ? (action.clear(), setConfirmation({ title: "停用组织", description: `停用 ${editing.name} 将限制其后续使用并保留历史。停用学校后本校账号不能继续访问。`, action: () => action.run(async key => (await (kind === "school" ? ManagementService.updateSchool({ body, path, headers: commandHeaders(key) }) : kind === "college" ? ManagementService.updateCollege({ body, path, headers: commandHeaders(key) }) : ManagementService.updateMajor({ body, path, headers: commandHeaders(key) }))).data,
          () => { setEditing(null); refresh() }, "组织信息已更新", JSON.stringify(["organization-update", kind, path, body])) })) : void action.run(async key => (await (kind === "school" ? ManagementService.updateSchool({ body, path, headers: commandHeaders(key) }) : kind === "college" ? ManagementService.updateCollege({ body, path, headers: commandHeaders(key) }) : ManagementService.updateMajor({ body, path, headers: commandHeaders(key) }))).data,
          () => { setEditing(null); refresh() }, "组织信息已更新", JSON.stringify(["organization-update", kind, path, body]))
      }}><Field label="名称"><input name="name" defaultValue={editing.name} maxLength={120} required /></Field><Field label="启用状态"><select name="is_active" defaultValue={String(editing.is_active)}><option value="true">启用</option><option value="false">停用</option></select></Field><div className="b1-actions"><Button type="submit"  disabled={action.pending}>保存组织信息</Button></div></form>
    </EditorDialog>}
    {creating && <EditorDialog title={`创建${names[kind]}`} pending={action.pending} onClose={() => setCreating(false)}><ActionFeedback action={action} /><OrganizationForm kind={kind} schools={choices.schools.data?.data ?? []} colleges={choices.colleges.data?.data ?? []} schoolId={choices.schoolId} collegeId={choices.collegeId} selectSchool={choices.selectSchool} selectCollege={choices.selectCollege} submit={create} pending={action.pending} /></EditorDialog>}
    <ConfirmCommand command={confirmation} action={action} onClose={() => setConfirmation(null)} />
  </BusinessPage>
}
