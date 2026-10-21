import { useState, type FormEvent } from "react"
import { Field, roleName } from "../teaching/ui"

export type SelectOption = { id: string; name: string }
export type EditableAccount = {
  id: string; username: string; display_name: string; student_no?: string | null;
  gender?: string | null; contact?: string | null; college_id?: string | null; major_id?: string | null
}

export function Options({ values, empty = "请选择" }: { values: SelectOption[]; empty?: string }) {
  return <><option value="">{empty}</option>{values.map(value => <option key={value.id} value={value.id}>{value.name}</option>)}</>
}

export function AccountForm({ schools, colleges, majors, schoolId, collegeId, selectSchool, selectCollege, allowedRoles,
  existing, pending, submit }: {
  schools: SelectOption[]; colleges: SelectOption[]; majors: SelectOption[]; schoolId: string; collegeId: string;
  selectSchool: (value: string) => void; selectCollege: (value: string) => void; allowedRoles: string[];
  existing?: EditableAccount; pending: boolean; submit: (form: HTMLFormElement) => void
}) {
  const [roles, setRoles] = useState<string[]>(allowedRoles.includes("student") ? ["student"] : allowedRoles.slice(0, 1))
  const student = roles.includes("student")
  function toggle(role: string, checked: boolean) {
    if (role === "student") setRoles(checked ? ["student"] : [])
    else setRoles(previous => checked ? [...previous.filter(value => value !== "student"), role] : previous.filter(value => value !== role))
  }
  function onSubmit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); submit(event.currentTarget) }
  return <form className="b1-form" onSubmit={onSubmit}>
    {!existing && <Field label="学校"><select name="school_id" value={schoolId} required onChange={event => selectSchool(event.target.value)}><Options values={schools} /></select></Field>}
    <Field label="所属学院"><select name="college_id" value={collegeId} required onChange={event => selectCollege(event.target.value)}><Options values={colleges} /></select></Field>
    <Field label="专业" hint="新建学生必须选择专业；教师和管理员可不填。"><select name="major_id" defaultValue={existing?.major_id ?? ""} required={!existing && student}><Options values={majors} empty="未选择专业" /></select></Field>
    <Field label="登录账号" hint="登录账号与学生学号分别保存。"><input name="username" defaultValue={existing?.username} required readOnly={Boolean(existing)} maxLength={80} pattern="[A-Za-z0-9_.@\-]+" autoComplete="off" /></Field>
    <Field label="姓名"><input name="display_name" defaultValue={existing?.display_name} required maxLength={80} autoComplete="off" /></Field>
    <Field label="独立学号" hint="学校内唯一；为学生填写正式学号。"><input name="student_no" defaultValue={existing?.student_no ?? ""} required={!existing && student} maxLength={80} autoComplete="off" /></Field>
    <Field label="性别（选填）"><select name="gender" defaultValue={existing?.gender ?? ""}><option value="">未填写</option><option value="male">男</option><option value="female">女</option><option value="other">其他</option><option value="unspecified">不愿说明</option></select></Field>
    <Field label="联系方式（选填）"><input name="contact" defaultValue={existing?.contact ?? ""} maxLength={120} autoComplete="off" /></Field>
    {!existing && <>
      <Field label="初始临时密码" hint="首次登录必须修改；本页不会显示已保存的密码。"><input name="temporary_password" type="password" required minLength={8} maxLength={256} autoComplete="new-password" /></Field>
      <fieldset className="b1-role-fields"><legend>初始角色</legend>{allowedRoles.map(role => <label key={role} className="b1-checkbox"><input type="checkbox" name="grant_role" value={role} checked={roles.includes(role)} onChange={event => toggle(role, event.target.checked)} />{roleName[role] ?? role}</label>)}<small>学生账号独立；教师可兼任管理员。学院管理员初始范围为所选学院。</small></fieldset>
    </>}
    <div className="b1-wide b1-actions"><button className="b1-button" disabled={pending || (!existing && !roles.length)}>{pending ? "正在保存…" : existing ? "保存账号资料" : "创建账号"}</button></div>
  </form>
}

export function OrganizationForm({ schools, colleges, schoolId, collegeId, kind, selectSchool, selectCollege, submit,
  pending }: { schools: SelectOption[]; colleges: SelectOption[]; schoolId: string; collegeId: string;
  kind: "school" | "college" | "major"; selectSchool: (value: string) => void; selectCollege: (value: string) => void;
  submit: (form: HTMLFormElement) => void; pending: boolean }) {
  return <form className="b1-form" onSubmit={event => { event.preventDefault(); submit(event.currentTarget) }}>
    {kind !== "school" && <Field label="所属学校"><select name="school_id" value={schoolId} required onChange={event => selectSchool(event.target.value)}><Options values={schools} /></select></Field>}
    {kind === "major" && <Field label="所属学院"><select name="college_id" value={collegeId} required onChange={event => selectCollege(event.target.value)}><Options values={colleges} /></select></Field>}
    <Field label="代码" hint="使用英文字母、数字、下划线或短横线。"><input name="code" required maxLength={40} pattern="[A-Za-z0-9_\-]+" /></Field>
    <Field label={kind === "school" ? "学校名称" : kind === "college" ? "学院名称" : "专业名称"}><input name="name" required maxLength={120} /></Field>
    <div className="b1-actions"><button className="b1-button" disabled={pending}>{pending ? "正在创建…" : "确认创建"}</button></div>
  </form>
}
