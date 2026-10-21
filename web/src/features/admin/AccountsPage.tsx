import { useCallback, useState } from "react"
import { ManagementService, type AccountCreateWritable, type AccountPatch, type AccountView, type GrantInput, type Role } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { CsvImporter } from "../teaching/CsvImporter"
import { FilterFields, ConfirmCommand, type ConfirmationCommand, EditorDialog, SearchFilters, BusinessRecords, Button, ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, input, Loading, nullable, Notice, Pager, roleName, Section, SessionPage, useBusinessAction, useBusinessQuery } from "../teaching/ui"
import { AccountForm, Options } from "./forms"
import { canManageAccount, grantRoles, useOrganizationChoices } from "./scope"

export function AccountsPage(page: PageProps) { return <SessionPage page={page}><AccountsBody {...page} /></SessionPage> }
function AccountsBody(page: PageProps) {
  const choices = useOrganizationChoices(page)
  const [confirmation, setConfirmation] = useState<ConfirmationCommand | null>(null)
  const action = useBusinessAction(page.session)
  const [term, setTerm] = useState("")
  const [q, setQ] = useState("")
  const [role, setRole] = useState<Role | undefined>(undefined)
  const [filterCollege, setFilterCollege] = useState("")
  const [offset, setOffset] = useState(0)
  const [createVisible, setCreateVisible] = useState(false)
  const [editing, setEditing] = useState<AccountView | null>(null)
  const rows = useBusinessQuery(page.session, useCallback(async signal => (await ManagementService.listAccounts({
    query: { school_id: choices.schoolId, college_id: filterCollege || undefined, role, q, offset, limit: 20 }, signal,
  })).data, [choices.schoolId, filterCollege, role, q, offset]), page.session.workRole === "administrator" && Boolean(choices.schoolId))
  const allowedRoles = grantRoles(page)
  function openAccount(row: AccountView) {
    choices.selectSchool(row.school_id ?? ""); choices.selectCollege(row.college_id ?? "")
    setEditing(row); setCreateVisible(false); action.clear()
  }
  function saveAccount(form: HTMLFormElement) {
    const common = { display_name: input(form, "display_name"), college_id: choices.collegeId,
      major_id: nullable(input(form, "major_id")), student_no: nullable(input(form, "student_no")),
      gender: nullable(input(form, "gender")) as AccountCreateWritable["gender"], contact: nullable(input(form, "contact")) }
    if (editing) {
      const body: AccountPatch = { ...common, revision: editing.revision }
      void action.run(async key => (await ManagementService.updateAccount({ path: { user_id: editing.id }, body, headers: commandHeaders(key) })).data,
        result => { setEditing(result); rows.reload() }, "账号资料已保存", JSON.stringify(["account-update", editing.id, body]))
    } else {
      const selected = new FormData(form).getAll("grant_role").map(String) as Role[]
      const body: AccountCreateWritable = { ...common, school_id: choices.schoolId, username: input(form, "username"),
        temporary_password: String(new FormData(form).get("temporary_password") ?? ""),
        grants: selected.map(value => ({ role: value, ...(value === "college_admin" ? { college_id: choices.collegeId } : {}) })) }
      void action.run(async key => {
        const created = (await ManagementService.createAccount({ body, headers: commandHeaders(key) })).data
        return (await ManagementService.getAccount({ path: { user_id: created.id } })).data
      },
        result => { form.reset(); setCreateVisible(false); setEditing(result); rows.reload() }, "账号已开通，首次登录须修改临时密码", JSON.stringify(["account-create", body]))
    }
  }
  const formChoices = { schools: choices.schools.data?.data ?? [], colleges: choices.colleges.data?.data ?? [],
    majors: choices.majors.data?.data ?? [], schoolId: choices.schoolId, collegeId: choices.collegeId,
    selectSchool: choices.selectSchool, selectCollege: choices.selectCollege, allowedRoles,
    pending: action.pending, submit: saveAccount }
  if (page.session.workRole !== "administrator") return <div className="b1-ui"><Notice kind="error">请使用管理员工作身份。</Notice></div>
  return <BusinessPage page={page} title="账号与授权" description="组织资料、独立学号与工作角色统一管理，所有变更由服务端校验范围。">
    {!createVisible && !editing && <ActionFeedback action={action} />}
    {(choices.schools.error || choices.colleges.error || choices.majors.error) && <Notice kind="error" retry={choices.reload}>{choices.schools.error || choices.colleges.error || choices.majors.error}</Notice>}
    <div className="b1-task-bar"><CsvImporter session={page.session} kind="accounts" schoolId={choices.schoolId} imported={rows.reload} />
      <Button onClick={() => { setEditing(null); setCreateVisible(true); action.clear() }}>新建账号</Button></div>
    <Section title="授权范围内的账号">
      <SearchFilters label="账号、姓名或学号" placeholder="输入姓名、账号或独立学号" value={term} onChange={setTerm} onSearch={() => { setQ(term.trim()); setOffset(0) }} onClear={() => { setTerm(""); setQ(""); setOffset(0) }}><FilterFields>
        <Field label="学校"><select value={choices.schoolId} onChange={event => { choices.selectSchool(event.target.value); setFilterCollege(""); setOffset(0); setEditing(null) }}><Options values={choices.schools.data?.data ?? []} /></select></Field>
        <Field label="学院范围"><select value={filterCollege} onChange={event => { setFilterCollege(event.target.value); setOffset(0) }}><Options values={choices.colleges.data?.data ?? []} empty="全部已授权学院" /></select></Field>
        <Field label="角色"><select value={role ?? ""} onChange={event => { setRole((event.target.value || undefined) as Role | undefined); setOffset(0) }}><option value="">全部角色</option>{(["student", "teacher", "college_admin", "school_admin"] as Role[]).map(value => <option key={value} value={value}>{roleName[value]}</option>)}</select></Field>
      </FilterFields></SearchFilters>
      {rows.loading ? <Loading /> : rows.error ? <Notice kind="error" retry={rows.reload}>{rows.error}</Notice> : rows.data?.count === 0 ? <Empty>当前范围内没有匹配的账号。</Empty> : rows.data && <>
        <BusinessRecords items={rows.data.data} itemKey={row => String(row.id)} titleLabel="姓名 / 登录账号" title={row => <>{row.display_name}<small>{row.username}</small></>} fields={[{ label: "学号", value: row => <>{row.student_no || "待补充 / 不适用"}</> }, { label: "角色与状态", value: row => <>{row.grants.map((grant, index) => <Badge key={index}>{roleName[grant.role]}</Badge>)}<Badge muted={!row.is_active}>{row.is_active ? "启用" : "停用"}</Badge>{row.must_change_password && <Badge muted>待首次改密</Badge>}</> }]} actionLabel="管理" actions={row => <>{canManageAccount(page, row) ? <Button type="button" variant="secondary" onClick={() => openAccount(row)}>编辑账号</Button> : <small>{row.id === page.user.id ? "本人资料使用个人设置" : "当前身份仅可查看"}</small>}</>} /><Pager offset={offset} count={rows.data.count} change={setOffset} />
      </>}
    </Section>
    {createVisible && <EditorDialog title="创建账号" pending={action.pending} onClose={() => setCreateVisible(false)}>
      <p className="b1-description">学生与教职账号分开；临时密码交给本人，首次登录必须修改。</p><ActionFeedback action={action} />
      <AccountForm key={`new:${choices.schoolId}`} {...formChoices} />
    </EditorDialog>}
    {editing && <EditorDialog title={`账号管理：${editing.display_name}`} pending={action.pending} savedVersion={editing.revision} onClose={() => setEditing(null)}>
      <p className="b1-description">登录账号：{editing.username} · 当前修订 {editing.revision}</p><ActionFeedback action={action} />
      {action.error && /修改|冲突|更新/.test(action.error) && <Notice kind="warning">当前输入未覆盖服务器资料。读取最新后请重新确认再保存。
        <Button variant="secondary" onClick={() => { void action.run(async () => (await ManagementService.getAccount({ path: { user_id: editing.id } })).data, result => setEditing(result), "已读取最新账号资料，请重新确认后保存") }}>读取最新账号资料</Button>
      </Notice>}
      {choices.majors.loading ? <Loading /> : <AccountForm key={`${editing.id}:${editing.revision}`} {...formChoices} existing={editing} />}
      <Section title="账号启用状态" description="停用将撤销旧会话；在用班级主教师须先完成交接。">
        <Button type="button" variant={editing.is_active ? "danger" : "secondary"} disabled={action.pending} onClick={() => {
          const body = { revision: editing.revision, is_active: !editing.is_active }
          editing.is_active ? (action.clear(), setConfirmation({ title: "停用账号", description: `${editing.display_name} 将被停用，全部旧会话失效；在用主讲教师须先完成交接。`, action: () => action.run(async key => (await ManagementService.updateAccount({ path: { user_id: editing.id }, body, headers: commandHeaders(key) })).data,
            result => { setEditing(result); rows.reload() }, editing.is_active ? "账号已停用，旧会话已撤销" : "账号已启用", JSON.stringify(["account-status", editing.id, body])) })) : void action.run(async key => (await ManagementService.updateAccount({ path: { user_id: editing.id }, body, headers: commandHeaders(key) })).data,
            result => { setEditing(result); rows.reload() }, editing.is_active ? "账号已停用，旧会话已撤销" : "账号已启用", JSON.stringify(["account-status", editing.id, body]))
        }}>{editing.is_active ? "停用此账号" : "重新启用账号"}</Button>
      </Section>
      <Section title="角色授权" description="只使用当前管理员范围；撤销授权后，旧会话的新请求立即重新判权。">
        <BusinessRecords items={editing.grants} itemKey={grant => `${grant.role}:${grant.college_id ?? "school"}`} titleLabel="角色" title={grant => <>{roleName[grant.role]}</>} fields={[{ label: "授权学院", value: grant => <>{grant.college_id ? choices.colleges.data?.data.find(value => value.id === grant.college_id)?.name ?? "已授权学院" : "学校 / 账号范围"}</> }]} actionLabel="操作" actions={grant => <><Button type="button" variant="danger" disabled={action.pending || !allowedRoles.includes(grant.role)} onClick={() => {
          ;(action.clear(), setConfirmation({ title: "撤销角色授权", description: `撤销 ${editing.display_name} 的 ${roleName[grant.role]} 授权；旧会话的新请求会重新判权。`, action: () => action.run(async key => (await ManagementService.revokeRole({ path: { user_id: editing.id }, body: grant, headers: commandHeaders(key) })).data,
            result => { setEditing(result); rows.reload() }, "授权已撤销", JSON.stringify(["revoke-role", editing.id, grant])) }))
        }}>撤销此授权</Button></>} />
        <form className="b1-filter" onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget
          const selected = input(form, "role") as Role
          const body: GrantInput = { role: selected, college_id: selected === "college_admin" ? input(form, "grant_college") : null }
          void action.run(async key => (await ManagementService.grantRole({ path: { user_id: editing.id }, body, headers: commandHeaders(key) })).data,
            result => { setEditing(result); rows.reload() }, "角色授权已保存", JSON.stringify(["grant-role", editing.id, body]))
        }}><Field label="新增角色"><select name="role" required>{allowedRoles.filter(value => editing.grants.some(g => g.role === "student") ? value === "student" : !editing.grants.length || value !== "student").map(value => <option key={value} value={value}>{roleName[value]}</option>)}</select></Field>
          <Field label="学院管理员授权范围"><select name="grant_college" defaultValue={choices.collegeId}><Options values={choices.colleges.data?.data ?? []} /></select></Field><Button type="submit" variant="secondary" disabled={action.pending}>添加授权</Button></form>
      </Section>
      <Section title="重置为临时密码" description="只影响这个账号，重置后撤销全部旧会话，再次登录必须改密。">
        <form className="b1-filter" onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget
          const body = { temporary_password: String(new FormData(form).get("password") ?? "") }
          ;(action.clear(), setConfirmation({ title: "重置账号密码", description: `将为 ${editing.display_name} 设置新的临时密码，撤销全部旧会话，并要求首次登录改密。`, action: () => action.run(async key => {
            await ManagementService.resetPassword({ path: { user_id: editing.id }, body, headers: commandHeaders(key) })
            return (await ManagementService.getAccount({ path: { user_id: editing.id } })).data
          }, result => { form.reset(); rows.reload(); setEditing(result) }, "密码已重置，旧会话已撤销", JSON.stringify(["reset-password", editing.id, body])) }))
        }}><Field label="新的临时密码"><input name="password" type="password" required minLength={8} maxLength={256} autoComplete="new-password" /></Field><Button type="submit" variant="danger" disabled={action.pending}>确认重置密码</Button></form>
      </Section>
    </EditorDialog>}
    <ConfirmCommand command={confirmation} action={action} onClose={() => setConfirmation(null)} />
  </BusinessPage>
}
