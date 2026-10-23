import { useCallback, useState } from "react"
import { Link } from "react-router"
import { LockKeyhole, RefreshCw } from "lucide-react"
import { CoursesService, type CoursePublic, type EnrollmentResult } from "../../client"
import { Button, Notice, PageContainer, Pagination, SearchFilters, StatePanel } from "../../components/labconnect"
import { EnrollmentLinks, enrollmentMessage, JoinClassDialog, LeaveClassDialog } from "./enrollment-ui"
import { useResource } from "../../components/labconnect/hooks"
import labBench from "../../components/labconnect/assets/illustrations/lab-bench.svg"
import chemistry from "../../components/labconnect/assets/illustrations/chemistry.svg"

export function StudentCoursesPage() {
  const [input, setInput] = useState(""), [query, setQuery] = useState(""), [offset, setOffset] = useState(0)
  const [joining, setJoining] = useState(false), [leaving, setLeaving] = useState<CoursePublic>(), [notice, setNotice] = useState<EnrollmentResult>()
  const size = 12
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await CoursesService.courses({ query: { q: query, offset, limit: size }, signal })).data, [query, offset]))
  return <PageContainer title="我的课程" description="查看已加入的教学班与授课教师。" actions={<><EnrollmentLinks /><Button onClick={() => setJoining(true)}>使用班级邀请码加入</Button><Button variant="secondary" onClick={() => { setNotice(undefined); resource.reload() }} pending={resource.loading}><RefreshCw size={17} />刷新</Button></>}>
    {notice && <Notice kind={notice.status.startsWith("pending_") ? "warning" : "success"}>{enrollmentMessage(notice)} <Link to="/student/enrollments">查看本人班级申请与历史</Link></Notice>}
    <section className="lc-course-intro"><div><p>实验室安全学习</p><h2>先了解规范，再走进实验室。</h2><p>这里汇集你已加入的课程。教师发布学习内容后，<br className="lc-desktop" />即可从对应课程开始学习。</p></div><img src={labBench} alt="" /></section>
    <SearchFilters value={input} onChange={setInput} label="搜索课程" placeholder="课程名称、代码或主讲教师" onSearch={() => { setQuery(input.trim()); setOffset(0) }} onClear={() => { setInput(""); setQuery(""); setOffset(0); resource.reload() }} />
    {resource.loading ? <StatePanel kind="loading" /> : resource.error ? <StatePanel kind="error" description={resource.error} retry={resource.reload} /> : resource.data && <>
      <h2 className="lc-list-title">已加入的教学班 <span data-testid="course-count">{resource.data.count}</span></h2>
      {resource.data.data.length ? <div className="lc-course-grid">{resource.data.data.map(course => <article className="lc-course-card" key={course.id}>
        <div className="lc-course-cover"><span>课程已建立</span><img src={chemistry} alt="" /></div><div className="lc-course-body"><p>{course.college_name} · {course.code}</p><h3>{course.title}</h3>
          <p className="lc-teacher"><span>{course.teacher_name.slice(0, 1)}</span>主讲教师：{course.teacher_name}</p><footer><span>当前在班 · 学习内容待教师发布</span><LockKeyhole size={15} /></footer><div className="lc-actions lc-enrollment-actions"><Link className="lc-button lc-secondary" to={`/student/courses/${course.id}`}>查看班级</Link><Button variant="quiet" onClick={() => setLeaving(course)}>退出教学班</Button></div></div></article>)}</div>
        : <StatePanel kind="empty" title={query ? "没有匹配的教学班" : offset ? "本页暂无教学班" : "暂未加入教学班"} description={query ? "尝试更换关键词或清空搜索。" : "请联系课程教师确认加入安排。"} />}
      <Pagination total={resource.data.count} offset={offset} pageSize={size} onChange={setOffset} /></>}
    {joining && <JoinClassDialog onClose={() => setJoining(false)} onConfirmed={result => { setJoining(false); setNotice(result); resource.reload() }} />}
    {leaving && <LeaveClassDialog course={leaving} onClose={() => setLeaving(undefined)} onConfirmed={result => { setLeaving(undefined); setNotice(result); resource.reload() }} />}
  </PageContainer>
}
