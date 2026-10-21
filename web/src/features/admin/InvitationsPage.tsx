import { useCallback, useEffect, useState } from "react"
import { ManagementService, type InvitationCreate, type InvitationIssued } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, formatTime, futureLocalDate, input, Loading, Notice, Pager, Section, SessionPage, useBusinessAction, useBusinessQuery, utcDate } from "../teaching/ui"
import { Options } from "./forms"
import { useOrganizationChoices } from "./scope"

export function InvitationsPage(page: PageProps) { return <SessionPage page={page}><InvitationsBody {...page} /></SessionPage> }
function InvitationsBody(page: PageProps) {
  const choices = useOrganizationChoices(page)
  const [offset, setOffset] = useState(0)
  const [issued, setIssued] = useState<InvitationIssued | null>(null)
  const action = useBusinessAction(page.session)
  const rows = useBusinessQuery(page.session, useCallback(async signal => (await ManagementService.listInvitations({ query: { offset, limit: 20 }, signal })).data, [offset]), page.session.workRole === "administrator")
  useEffect(() => { setIssued(null) }, [choices.schoolId, choices.collegeId])
  if (page.session.workRole !== "administrator") return <div className="b1-ui"><Notice kind="error">请使用管理员工作身份。</Notice></div>
  return <BusinessPage page={page} title="学生账号邀请" description="限定学校、学院、专业和使用次数，学生用自己的密码开通独立账号。">
    <ActionFeedback action={action} />
    {(choices.schools.error || choices.colleges.error || choices.majors.error) && <Notice kind="error" retry={choices.reload}>{choices.schools.error || choices.colleges.error || choices.majors.error}</Notice>}
    <Section title="创建开通邀请" description="此邀请用于创建学生账号；加入教学班使用班级管理页的邀请码。">
      <form className="b1-form" onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body: InvitationCreate = { school_id: choices.schoolId, college_id: choices.collegeId,
          major_id: input(form, "major_id") || null, max_uses: Number(input(form, "max_uses")), expires_at: new Date(input(form, "expires_at")).toISOString() }
        void action.run(async key => (await ManagementService.createInvitation({ body, headers: commandHeaders(key) })).data,
          result => { setIssued(result); rows.reload() }, "邀请已生成", JSON.stringify(["invitation-create", body]))
      }}>
        <Field label="学校"><select value={choices.schoolId} required onChange={event => choices.selectSchool(event.target.value)}><Options values={choices.schools.data?.data ?? []} /></select></Field>
        <Field label="学院"><select value={choices.collegeId} required onChange={event => choices.selectCollege(event.target.value)}><Options values={choices.colleges.data?.data ?? []} /></select></Field>
        <Field label="限定专业"><select name="major_id"><Options values={choices.majors.data?.data ?? []} empty="由学生选择本学院专业" /></select></Field>
        <Field label="最多使用次数"><input name="max_uses" type="number" required min={1} max={500} defaultValue={1} /></Field>
        <Field label="有效期至（本机时区）"><input name="expires_at" type="datetime-local" required defaultValue={futureLocalDate()} /></Field>
        <div className="b1-actions"><button className="b1-button" disabled={action.pending || !choices.collegeId}>{action.pending ? "正在生成…" : "生成学生账号邀请"}</button></div>
      </form>
      {issued && <Notice kind="success"><strong>本次生成的邀请码</strong><code className="b1-code">{issued.code}</code><span>学校代码：{choices.schools.data?.data.find(value => value.id === issued.school_id)?.code ?? "请使用本校登录代码"}；有效期至 {formatTime(issued.expires_at)}。请交给对应学生，完整注册入口由学习端接入。</span></Notice>}
    </Section>
    <Section title="授权范围内的邀请" description="列表不返回邀请码明文；需要新邀请时重新生成，可随时撤销未使用的邀请。">
      {rows.loading ? <Loading /> : rows.error ? <Notice kind="error" retry={rows.reload}>{rows.error}</Notice> : rows.data?.count === 0 ? <Empty>尚未创建账号邀请。</Empty> : rows.data && <>
        <div className="b1-table-wrap"><table className="b1-table"><thead><tr><th>学院 / 专业</th><th>使用情况</th><th>有效期</th><th>状态与操作</th></tr></thead><tbody>{rows.data.data.map(row => <tr key={row.id}><td>{choices.colleges.data?.data.find(value => value.id === row.college_id)?.name ?? "已授权学院"}<small>{row.major_id ? "已限定专业" : "学生选择学院内专业"}</small></td><td>{row.used_count} / {row.max_uses}</td><td>{formatTime(row.expires_at)}</td><td><Badge muted={row.revoked || row.used_count >= row.max_uses || utcDate(row.expires_at).getTime() <= Date.now()}>{row.revoked ? "已撤销" : row.used_count >= row.max_uses ? "次数已满" : utcDate(row.expires_at).getTime() <= Date.now() ? "已到期" : "有效"}</Badge><button className="b1-button b1-danger" type="button" disabled={action.pending || row.revoked} onClick={() => {
          void action.run(async key => (await ManagementService.revokeInvitation({ path: { invitation_id: row.id }, headers: commandHeaders(key) })).data,
            () => { if (issued?.id === row.id) setIssued(null); rows.reload() }, "邀请已撤销", JSON.stringify(["invitation-revoke", row.id]))
        }}>撤销邀请</button></td></tr>)}</tbody></table></div><Pager offset={offset} count={rows.data.count} change={setOffset} />
      </>}
    </Section>
  </BusinessPage>
}
