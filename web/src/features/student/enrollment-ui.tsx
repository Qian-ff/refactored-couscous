import { useState, type FormEvent } from "react"
import { Link } from "react-router"
import { TeachingService, type CoursePublic, type EnrollmentResult } from "../../client"
import { Button, Dialog, Field, Notice } from "../../components/labconnect"
import { useCommand } from "../../components/labconnect/hooks"

export const requestStatus: Record<string, string> = { pending: "待审批", approved: "已批准", rejected: "未批准", canceled: "已撤销" }
export function dateLabel(value?: string | null) {
  if (!value) return "尚未处理"
  const date = new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(value) ? value : value + "Z")
  return Number.isNaN(date.getTime()) ? "时间不可用" : date.toLocaleString("zh-CN", { hour12: false })
}
export function enrollmentMessage(result: EnrollmentResult) {
  return ({ active: "服务端已确认当前在班。", pending_join: "加入申请待审批，批准前尚未加入教学班。", pending_leave: "退出申请待审批，批准前仍保持原在班关系。", withdrawn: "服务端已确认退出教学班，当前课程访问权限已撤销。" } as Record<string, string>)[result.status]
    || "服务端状态已返回，请重新读取当前班级关系。"
}
export function JoinClassDialog({ onClose, onConfirmed }: { onClose: () => void; onConfirmed: (result: EnrollmentResult) => void }) {
  const [code, setCode] = useState("")
  const action = useCommand()
  async function submit(event: FormEvent) {
    event.preventDefault()
    const body = { invitation_code: code.trim() }
    const response = await action.run(JSON.stringify(body), key => TeachingService.joinClass({ body, headers: { "Idempotency-Key": key } }))
    if (response) onConfirmed(response.data)
  }
  return <Dialog title="使用班级邀请码加入" busy={action.pending} onClose={onClose}>
    <p>此入口用于已开通的学生加入教学班。学生账号邀请用于注册账号，不能代替班级邀请码。</p>
    <form className="lc-form" onSubmit={submit}><Field label="班级邀请码" hint="请输入课程教师提供的完整代码。旧码轮换、失效或过期时请联系教师。">
      <textarea name="class-code" value={code} onChange={event => setCode(event.target.value)} required minLength={16} maxLength={100} autoComplete="off" spellCheck={false} disabled={action.pending} /></Field>
      {action.error && <Notice kind="error">{action.error}<p>结果未确认时，保留原代码重试同一请求；也可重新读取本人申请与班级关系。</p></Notice>}
      <div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={onClose}>取消</Button><Button type="submit" pending={action.pending}>确认加入教学班</Button></div>
    </form>
  </Dialog>
}
export function LeaveClassDialog({ course, onClose, onConfirmed }: { course: CoursePublic; onClose: () => void; onConfirmed: (result: EnrollmentResult) => void }) {
  const action = useCommand()
  return <Dialog title="退出教学班" busy={action.pending} onClose={onClose}><p>教学班：<strong>{course.title}</strong></p><p>代码：{course.code}</p>
    <Notice kind="warning">是否需要教师审批由本班设置决定。直接退出或批准退出后，将不能继续访问当前课程内容；本人历史关系仍按学校规则保留。</Notice>
    {action.error && <Notice kind="error">{action.error}<p>服务端结果尚未确认时，可重试原请求。若班级状态已变化，请重新读取。</p></Notice>}
    <div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={onClose}>保留在班</Button><Button variant="danger" pending={action.pending} onClick={async () => {
      const response = await action.run("leave:" + course.id, key => TeachingService.leaveClass({ path: { course_id: course.id }, headers: { "Idempotency-Key": key } }))
      if (response) onConfirmed(response.data)
    }}>确认退出教学班</Button></div>
  </Dialog>
}
export function EnrollmentLinks() {
  return <Link className="lc-button lc-secondary" to="/student/enrollments">班级申请与历史</Link>
}
