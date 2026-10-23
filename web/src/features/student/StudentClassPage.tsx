import { useCallback, useState } from "react"
import { Link } from "react-router"
import { CoursesService } from "../../client"
import { Button, Notice, PageContainer, Panel, StatePanel } from "../../components/labconnect"
import { useResource } from "../../components/labconnect/hooks"
import type { PageProps } from "../../lib/extensions"
import { enrollmentMessage, EnrollmentLinks, LeaveClassDialog } from "./enrollment-ui"

export function StudentClassPage({ params }: PageProps) {
  const courseId = params.courseId || ""
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await CoursesService.course({ path: { course_id: courseId }, signal })).data, [courseId]))
  const [leaving, setLeaving] = useState(false), [notice, setNotice] = useState("")
  if (resource.loading) return <PageContainer title="教学班"><StatePanel kind="loading" /></PageContainer>
  if (resource.error || !resource.data) return <PageContainer title="教学班">{notice && <Notice>{notice}</Notice>}<StatePanel kind={[403, 404].includes(resource.status || 0) ? "forbidden" : "error"}
    title={[403, 404].includes(resource.status || 0) ? "教学班当前不可访问" : "教学班读取失败"} description={resource.error} retry={resource.reload} /><Link className="lc-button lc-secondary" to="/student/courses">返回我的课程</Link><EnrollmentLinks /></PageContainer>
  const course = resource.data
  return <PageContainer title={course.title} description="当前在班关系及访问范围由服务端校验。" actions={<><EnrollmentLinks /><Button variant="secondary" onClick={resource.reload}>刷新班级状态</Button></>}>
    {notice && <Notice>{notice}</Notice>}<Panel title="教学班信息"><dl className="lc-profile-facts"><div><dt>教学班代码</dt><dd>{course.code}</dd></div><div><dt>学院</dt><dd>{course.college_name}</dd></div><div><dt>主讲教师</dt><dd>{course.teacher_name}</dd></div><div><dt>当前关系</dt><dd>当前在班</dd></div></dl></Panel>
    <StatePanel kind="unavailable" title="学习内容待教师发布" description="题库、考试、助手和培训记录尚未开放。" />
    <div className="lc-actions"><Link className="lc-button lc-secondary" to="/student/courses">返回我的课程</Link><Button variant="danger" onClick={() => setLeaving(true)}>退出教学班</Button></div>
    {leaving && <LeaveClassDialog course={course} onClose={() => setLeaving(false)} onConfirmed={result => {
      setLeaving(false)
      setNotice(enrollmentMessage(result)); resource.reload()
    }} />}
  </PageContainer>
}
