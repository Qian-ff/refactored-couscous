import { useCallback, useEffect, useState } from "react"
import { TeachingService, type ClassManagementView, type JoinCodeIssued } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { Options } from "../admin/forms"
import { CsvImporter } from "./CsvImporter"
import { FilterFields, CopyCode, Dialog, SearchFilters, BusinessRecords, Button, ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, formatTime, futureLocalDate, input, Loading, Notice, Pager, Section, SessionPage, useBusinessAction, useBusinessQuery } from "./ui"

export function ClassManagementPage(page: PageProps) { return <SessionPage page={page}><ClassManagementBody {...page} /></SessionPage> }
function ClassManagementBody(page: PageProps) {
  const courseId = page.params.courseId ?? ""
  const path = { course_id: courseId }
  const back = page.session.workRole === "administrator" ? "/administration/courses" : "/teaching/courses"
  const [memberTerm, setMemberTerm] = useState("")
  const [memberQ, setMemberQ] = useState("")
  const [memberStatus, setMemberStatus] = useState("active")
  const [memberOffset, setMemberOffset] = useState(0)
  const [teacherTerm, setTeacherTerm] = useState("")
  const [teacherQ, setTeacherQ] = useState("")
  const [selectedTeacher, setSelectedTeacher] = useState("")
  const [issued, setIssued] = useState<JoinCodeIssued | null>(null)
  const [confirmTransfer, setConfirmTransfer] = useState(false)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const [archiveCode, setArchiveCode] = useState("")
  const [requestOffset, setRequestOffset] = useState(0)
  const [requestStatus, setRequestStatus] = useState("pending")
  const action = useBusinessAction(page.session)
  const state = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.classManagement({ path: { course_id: courseId }, signal })).data, [courseId]), Boolean(courseId))
  const record = state.data
  const editable = Boolean(record && !record.archived)
  const primary = editable && Boolean(record?.can_manage_staff)
  const staff = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.listStaff({ path: { course_id: courseId }, query: { limit: 100 }, signal })).data, [courseId]), Boolean(record))
  const members = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.members({ path: { course_id: courseId }, query: { q: memberQ, status: memberStatus, offset: memberOffset, limit: 20 }, signal })).data, [courseId, memberQ, memberStatus, memberOffset]), Boolean(record))
  const requests = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.requests({ path: { course_id: courseId }, query: { status: requestStatus, offset: requestOffset, limit: 20 }, signal })).data, [courseId, requestStatus, requestOffset]), Boolean(record))
  const teachers = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.teacherOptions({ path: { course_id: courseId }, query: { q: teacherQ }, signal })).data, [courseId, teacherQ]), primary && teacherQ.length >= 2)
  useEffect(() => { setIssued(null); setSelectedTeacher(""); setConfirmArchive(false); setArchiveCode(""); setConfirmTransfer(false) }, [courseId])
  function refresh() { state.reload(); staff.reload(); members.reload(); requests.reload() }
  function applied(value: ClassManagementView) { if (!value.can_manage_members) page.navigate(back); else refresh() }
  if (!courseId) return <div className="b1-ui"><Notice kind="error">未提供教学班，请从课程列表进入。</Notice><Button type="submit"  onClick={() => page.navigate(back)}>返回课程列表</Button></div>
  return <BusinessPage page={page} title={record?.title ?? "教学班管理"} description="名单、教师协作与审批按本班授权；同一课程的其他教学班数据独立。">
    <div className="b1-actions"><Button type="button" variant="secondary" onClick={() => page.navigate(back)}>返回课程列表</Button><Button type="button" variant="secondary" onClick={refresh}>刷新本班数据</Button>{record && <Badge muted={record.archived}>{record.archived ? "已归档 · 历史只读" : "正在开课"} · {record.code}</Badge>}</div>
    {!confirmTransfer && !confirmArchive && <ActionFeedback action={action} />}
    {action.error && /修改|冲突|更新/.test(action.error) && <Notice kind="warning">未保存的输入没有覆盖服务器资料。<Button variant="secondary" onClick={refresh}>读取最新班级资料</Button></Notice>}
    {state.loading && <Loading />}{state.error && <Notice kind="error" retry={state.reload}>{state.error}</Notice>}
    {record && <>
      <nav className="b1-tabs" aria-label="班级管理区域">{[["settings", "班级概览"], ["members", "学生名单"], ["requests", "申请审批"], ["staff", "教师协作"]].map(([id, title]) => <Button key={id} variant="secondary" onClick={() => document.getElementById(`b1-${courseId}-${id}`)?.scrollIntoView({ block: "start" })}>{title}</Button>)}</nav>
      {record.archived && <Notice>本班已归档，历史名单和教师关系保留；学生不再通过此班访问当前资料。</Notice>}
      {!record.can_manage_staff && <Notice>当前为协作教学权限，可以教学及调整本班名单；教师授权、交接和归档由主讲教师或授权管理员操作。</Notice>}
      <Section id={`b1-${courseId}-settings`} title="班级设置">
        <form className="b1-form" key={`${record.id}:${record.revision}`} onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget
          const body = { revision: record.revision, title: input(form, "title"), join_approval: new FormData(form).has("join_approval"), leave_approval: new FormData(form).has("leave_approval") }
          void action.run(async key => (await TeachingService.updateSettings({ path, body, headers: commandHeaders(key) })).data,
            applied, "班级设置已保存", JSON.stringify(["class-settings", path, body]))
        }}><Field label="教学班名称"><input name="title" defaultValue={record.title} required maxLength={120} readOnly={!primary} disabled={action.pending} /></Field>
          <div><label className="b1-checkbox"><input name="join_approval" type="checkbox" defaultChecked={record.join_approval} disabled={!primary || action.pending} />加入本班需要审批</label><label className="b1-checkbox"><input name="leave_approval" type="checkbox" defaultChecked={record.leave_approval} disabled={!primary || action.pending} />退出本班需要审批</label></div>
          {primary && <div className="b1-actions"><Button type="submit"  disabled={action.pending}>保存班级设置</Button></div>}
        </form>
      </Section>
      <Section id={`b1-${courseId}-members`} title="学生名单" description="只提供本班教学所需的姓名、账号、学号和学院信息。">
        <SearchFilters label="搜索本班学生" placeholder="账号、姓名或学号" value={memberTerm} onChange={setMemberTerm} onSearch={() => { setMemberQ(memberTerm.trim()); setMemberOffset(0) }} onClear={() => { setMemberTerm(""); setMemberQ(""); setMemberOffset(0) }}><FilterFields>
          <Field label="名单状态"><select value={memberStatus} onChange={event => { setMemberStatus(event.target.value); setMemberOffset(0) }}><option value="active">当前在班</option><option value="all">包含退出与移出历史</option><option value="withdrawn">已退出</option><option value="removed">已移出</option></select></Field>
        </FilterFields></SearchFilters>
        {members.loading ? <Loading /> : members.error ? <Notice kind="error" retry={members.reload}>{members.error}</Notice> : members.data?.count === 0 ? <Empty>没有符合条件的本班学生。</Empty> : members.data && <>
          <BusinessRecords items={members.data.data} itemKey={row => String(row.id)} titleLabel="姓名 / 账号" title={row => <>{row.display_name}<small>{row.username}</small></>} fields={[{ label: "独立学号", value: row => <>{row.student_no ?? "待补充"}</> }, { label: "选课状态", value: row => <><Badge muted={row.status !== "active"}>{row.status === "active" ? "在班" : row.status === "removed" ? "已移出" : "已退出"}</Badge></> }]} actionLabel="名单操作" actions={row => <>{editable && <Button variant={row.status === "active" ? "danger" : "secondary"} type="button" disabled={action.pending} onClick={() => {
            const body = { username: row.username }
            void action.run(async key => (await (row.status === "active" ? TeachingService.removeMember({ path, body, headers: commandHeaders(key) }) : TeachingService.addMember({ path, body, headers: commandHeaders(key) }))).data,
              () => { members.reload(); requests.reload() }, row.status === "active" ? "学生已移出，历史保留" : "学生已加入本班", JSON.stringify(["member", path, row.status, body]))
          }}>{row.status === "active" ? "移出本班" : "重新加入"}</Button>}</>} /><Pager offset={memberOffset} count={members.data.count} change={setMemberOffset} />
        </>}
        {editable && <form className="b1-filter" onSubmit={event => {
          event.preventDefault(); const form = event.currentTarget; const body = { username: input(form, "username") }
          void action.run(async key => (await TeachingService.addMember({ path, body, headers: commandHeaders(key) })).data,
            () => { form.reset(); members.reload(); requests.reload() }, "学生已加入本班", JSON.stringify(["add-member", path, body]))
        }}><Field label="拉入已开通学生" hint="输入本校学生的准确登录账号，不开放其他学院完整账号目录。"><input name="username" required maxLength={80} placeholder="学生登录账号" /></Field><Button type="submit"  disabled={action.pending}>加入本班</Button></form>}
      </Section>
      <Section id={`b1-${courseId}-requests`} title="加入与退出审批">
        <Field label="审批状态"><select value={requestStatus} onChange={event => { setRequestStatus(event.target.value); setRequestOffset(0) }}><option value="pending">待处理</option><option value="all">全部历史</option></select></Field>
        {requests.loading ? <Loading /> : requests.error ? <Notice kind="error" retry={requests.reload}>{requests.error}</Notice> : requests.data?.count === 0 ? <Empty>没有符合条件的申请。</Empty> : requests.data && <>
          <BusinessRecords items={requests.data.data} itemKey={row => String(row.id)} titleLabel="学生" title={row => <>{row.display_name}</>} fields={[{ label: "申请类型", value: row => <>{row.kind === "join" ? "加入本班" : "退出本班"}</> }, { label: "时间 / 状态", value: row => <>{formatTime(row.created_at)}<small>{({ pending: "待处理", approved: "已同意", rejected: "已拒绝", canceled: "已取消" } as Record<string, string>)[row.status] ?? row.status}</small></> }]} actionLabel="处理" actions={row => <>{editable && row.status === "pending" && <div className="b1-actions">{[true, false].map(approve => <Button key={String(approve)} type="button" variant={approve ? "primary" : "secondary"} disabled={action.pending} onClick={() => {
            void action.run(async key => (await TeachingService.decideRequest({ path: { ...path, request_id: row.id }, body: { approve }, headers: commandHeaders(key) })).data,
              () => { members.reload(); requests.reload() }, "申请已处理", JSON.stringify(["decide-request", row.id, approve]))
          }}>{approve ? "同意" : "拒绝"}</Button>)}</div>}</>} /><Pager offset={requestOffset} count={requests.data.count} change={setRequestOffset} />
        </>}
      </Section>
      {editable && <Section title="批量加入学生"><CsvImporter session={page.session} kind="roster" schoolId={record.school_id} courseId={record.id} imported={() => { members.reload(); requests.reload() }} /></Section>}
      <Section id={`b1-${courseId}-staff`} title="教师协作" description="保留教师关系历史；协作教师可教学和管理名单，主讲教师负责关键授权。">
        {staff.loading ? <Loading /> : staff.error ? <Notice kind="error" retry={staff.reload}>{staff.error}</Notice> : staff.data && <BusinessRecords items={staff.data.data} itemKey={row => String(row.user_id)} titleLabel="教师" title={row => <>{row.display_name}</>} fields={[{ label: "班级角色", value: row => <>{row.is_primary ? "主讲教师" : "协作教师"}</> }, { label: "授权状态", value: row => <><Badge muted={!row.is_active}>{row.is_active ? "有效" : "已移除"}</Badge></> }]} actionLabel="操作" actions={row => <>{primary && !row.is_primary && <Button type="button" variant={row.is_active ? "danger" : "secondary"} disabled={action.pending} onClick={() => {
          const body = { revision: record.revision, teacher_id: row.user_id }
          void action.run(async key => (await (row.is_active ? TeachingService.removeStaff({ path, body, headers: commandHeaders(key) }) : TeachingService.addStaff({ path, body, headers: commandHeaders(key) }))).data,
            applied, "教师协作授权已更新", JSON.stringify(["staff-state", path, row.is_active, body]))
        }}>{row.is_active ? "移除协作" : "恢复协作"}</Button>}</>} />}
        {primary && <>
          <form className="b1-filter" onSubmit={event => { event.preventDefault(); setTeacherQ(teacherTerm.trim()); setSelectedTeacher(""); setConfirmTransfer(false) }}><Field label="查找本校教师" hint="至少输入2个字；只返回协作所需的最小信息。"><input value={teacherTerm} onKeyDown={event => { if (event.key === "Enter" && event.nativeEvent.isComposing) event.preventDefault() }} onChange={event => setTeacherTerm(event.target.value)} minLength={2} maxLength={100} required placeholder="教师姓名或账号" /></Field><Button type="submit" variant="secondary">查找教师</Button></form>
          {teachers.loading && <Loading />}{teachers.error && <Notice kind="error" retry={teachers.reload}>{teachers.error}</Notice>}
          {teachers.data?.count === 0 && <Empty>未找到匹配的本校教师。</Empty>}
          {teachers.data && teachers.data.count > 0 && <><Field label="选择教师"><select value={selectedTeacher} onChange={event => { setSelectedTeacher(event.target.value); setConfirmTransfer(false) }}><Options values={teachers.data.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` }))} /></select></Field>
            <div className="b1-actions"><Button  type="button" disabled={action.pending || !selectedTeacher} onClick={() => {
              const body = { revision: record.revision, teacher_id: selectedTeacher }
              void action.run(async key => (await TeachingService.addStaff({ path, body, headers: commandHeaders(key) })).data,
                value => { setSelectedTeacher(""); applied(value) }, "协作教师已添加", JSON.stringify(["staff-add", path, body]))
            }}>添加为协作教师</Button><Button variant="secondary" type="button" disabled={action.pending || !selectedTeacher} onClick={() => setConfirmTransfer(true)}>转交为主讲教师</Button></div>
          </>}
          {confirmTransfer && selectedTeacher && <Dialog title="转交主讲教师" busy={action.pending} onClose={() => setConfirmTransfer(false)}><ActionFeedback action={action} /><p>确认将主讲教师转交给所选教师？原主讲教师会失去本班当前授权，历史保留。</p><div className="b1-actions"><Button type="button"  disabled={action.pending} onClick={() => {
            const body = { revision: record.revision, teacher_id: selectedTeacher }
            void action.run(async key => (await TeachingService.transferClass({ path, body, headers: commandHeaders(key) })).data,
              value => { setConfirmTransfer(false); applied(value) }, "主讲教师已交接", JSON.stringify(["class-transfer", path, body]))
          }}>确认转交主讲教师</Button><Button type="button" variant="secondary" onClick={() => setConfirmTransfer(false)}>取消</Button></div></Dialog>}
        </>}
      </Section>
      {primary && <Section title="班级邀请码" description="用于已开通学生加入本班；重新生成后，旧邀请码立即失效。">
        <form className="b1-filter" onSubmit={event => {
          event.preventDefault(); const body = { revision: record.revision, expires_at: new Date(input(event.currentTarget, "expires_at")).toISOString() }
          void action.run(async key => (await TeachingService.rotateJoinCode({ path, body, headers: commandHeaders(key) })).data,
            value => { setIssued(value); state.reload() }, "本班邀请码已生成", JSON.stringify(["class-invite", path, body]))
        }}><Field label="有效期至（本机时区）"><input name="expires_at" type="datetime-local" required defaultValue={futureLocalDate(7)} /></Field><Button type="submit"  disabled={action.pending}>生成新班级邀请码</Button></form>
        {issued && <Notice kind="success"><span>本次生成的邀请码</span><code className="b1-code">{issued.code}</code><CopyCode value={issued.code} /><span>有效期至 {formatTime(issued.expires_at)}</span></Notice>}
      </Section>}
      {primary && <Section title="归档教学班" description="有历史的教学班通过归档结束使用，保留名单、教师和审批历史。">
        {!confirmArchive ? <Button variant="danger" type="button" onClick={() => { setArchiveCode(""); setConfirmArchive(true) }}>归档本教学班</Button> : <Dialog title="归档教学班" busy={action.pending} onClose={() => setConfirmArchive(false)}><ActionFeedback action={action} /><p>归档 {record.title} 后停止新选课和当前资料访问，历史只读。请输入代码 {record.code} 确认。</p><Field label="输入教学班代码确认归档"><input value={archiveCode} onChange={event => setArchiveCode(event.target.value)} autoComplete="off" /></Field><div className="b1-actions"><Button variant="danger" type="button" disabled={action.pending || archiveCode.trim() !== record.code} onClick={() => {
          const body = { revision: record.revision }
          void action.run(async key => (await TeachingService.archiveClass({ path, body, headers: commandHeaders(key) })).data,
            () => { setConfirmArchive(false); setIssued(null); refresh() }, "教学班已归档，历史保留", JSON.stringify(["class-archive", path, body]))
        }}>确认归档</Button><Button variant="secondary" type="button" onClick={() => setConfirmArchive(false)}>取消归档</Button></div></Dialog>}
      </Section>}
      <Notice>正式考试、学习进度和培训记录暂未开放。本页提供教学班设置、名单和教师协作管理。</Notice>
    </>}
  </BusinessPage>
}
