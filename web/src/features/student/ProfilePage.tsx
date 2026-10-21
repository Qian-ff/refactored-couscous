import { useCallback, useState, type FormEvent } from "react"
import { Link } from "react-router"
import { ManagementService } from "../../client"
import { Button, Field, Notice, PageContainer, Panel, StatePanel } from "../../components/labconnect"
import { genderOptions, type Gender } from "../../components/labconnect/AccountEntry"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import type { PageProps } from "../../lib/extensions"
import axios from "axios"

export function ProfilePage({ user }: PageProps) {
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await ManagementService.getProfile({ signal })).data, []))
  const action = useCommand(), [success, setSuccess] = useState(""), [conflict, setConflict] = useState(false)
  if (resource.loading) return <PageContainer title="本人资料"><StatePanel kind="loading" /></PageContainer>
  if (resource.error || !resource.data) return <PageContainer title="本人资料"><StatePanel kind="error" description={resource.error} retry={resource.reload} /></PageContainer>
  const profile = resource.data
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); setSuccess(""); setConflict(false)
    const body = { revision: profile.revision, gender: String(form.get("gender")) as Gender, contact: String(form.get("contact")).trim() || null }
    const result = await action.run(JSON.stringify(body), async key => {
      try { return await ManagementService.updateProfile({ body, headers: { "Idempotency-Key": key } }) }
      catch (reason) { if (axios.isAxiosError(reason) && reason.response?.status === 409) { setConflict(true); resource.reload() } throw reason }
    })
    if (result) { setSuccess("本人资料已保存"); resource.reload() }
  }
  return <PageContainer title="本人资料" description="学校及身份资料由管理员维护；你可以更新性别和联系方式。" actions={<Link className="lc-button lc-secondary" to="/account/password">修改密码</Link>}>
    {success && <Notice kind="success">{success}</Notice>}{conflict && <Notice kind="warning">资料已被更新，已重新读取最新版本。请核对后再次保存。</Notice>}
    <Panel title="账号与身份"><dl className="lc-profile-facts">{[["姓名", profile.display_name], ["登录账号", profile.username], ["学生学号", profile.student_no || "不适用"], ["学校", user.school?.name || "平台运维"], ["学院", user.college?.name || "按授权范围"], ["专业编号", profile.major_id || "未填写"]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></Panel>
    <Panel title="联系方式"><form key={profile.revision} className="lc-form" onSubmit={save}><div className="lc-form-grid"><Field label="性别（选填）"><select name="gender" defaultValue={profile.gender || "unspecified"}>{genderOptions}</select></Field>
      <Field label="联系方式（选填）"><input name="contact" maxLength={120} defaultValue={profile.contact || ""} autoComplete="tel" /></Field></div>
      {action.error && <Notice kind="error">{action.error}</Notice>}<div className="lc-actions"><Button type="submit" pending={action.pending}>保存本人资料</Button><Button variant="secondary" disabled={action.pending} onClick={resource.reload}>重新读取</Button></div></form></Panel>
  </PageContainer>
}
