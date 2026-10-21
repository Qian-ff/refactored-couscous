import { useCallback, useState } from "react"
import { CoursesService, TeachingService, type CatalogView, type CourseCreate, type CoursePublic } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { Options } from "../admin/forms"
import { canManageCatalog, isSchoolManager } from "../admin/scope"
import { ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, input, Loading, Notice, Pager, Section, SessionPage, useBusinessAction, useBusinessQuery } from "./ui"

export function CoursesPage(page: PageProps) { return <SessionPage page={page}><CoursesBody {...page} /></SessionPage> }
function CoursesBody(page: PageProps) {
  const [term, setTerm] = useState("")
  const [q, setQ] = useState("")
  const [catalogOffset, setCatalogOffset] = useState(0)
  const [classOffset, setClassOffset] = useState(0)
  const [catalogFilter, setCatalogFilter] = useState("")
  const [archived, setArchived] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedCatalog, setSelectedCatalog] = useState<CatalogView | null>(null)
  const [editingCatalog, setEditingCatalog] = useState<CatalogView | null>(null)
  const [collegeChoice, setCollegeChoice] = useState("")
  const [teacherChoice, setTeacherChoice] = useState("")
  const [teacherTerm, setTeacherTerm] = useState("")
  const [teacherQ, setTeacherQ] = useState("")
  const [created, setCreated] = useState<{ course: CoursePublic; assignedToSelf: boolean } | null>(null)
  const action = useBusinessAction(page.session)
  const context = useBusinessQuery(page.session, useCallback(async signal => (await CoursesService.context({ signal })).data, []))
  const catalogs = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.catalogs({ query: { q, archived, offset: catalogOffset, limit: 20 }, signal })).data, [q, archived, catalogOffset]))
  const classes = useBusinessQuery(page.session, useCallback(async signal => (await CoursesService.courses({ query: { q, archived, catalog_id: catalogFilter || undefined, offset: classOffset, limit: 20 }, signal })).data, [q, archived, catalogFilter, classOffset]))
  const pickerCatalog = selectedCatalog ?? editingCatalog
  const teachers = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.catalogTeacherOptions({ path: { catalog_id: pickerCatalog?.id ?? "" }, query: { q: teacherQ }, signal })).data, [pickerCatalog?.id, teacherQ]), Boolean(pickerCatalog && teacherQ.length >= 2 && canManageCatalog(page, pickerCatalog)))
  const colleges = selectedCatalog && !isSchoolManager(page)
    ? [{ id: selectedCatalog.college_id, name: context.data?.colleges.find(value => value.id === selectedCatalog.college_id)?.name ?? "课程目录所属学院（已授权）", school_id: selectedCatalog.school_id }]
    : context.data?.colleges ?? []
  const collegeId = collegeChoice && colleges.some(value => value.id === collegeChoice) ? collegeChoice : colleges[0]?.id ?? ""
  const schoolId = selectedCatalog?.school_id ?? colleges.find(value => value.id === collegeId)?.school_id
  const candidates = [...(context.data?.teachers.filter(value => value.school_id === schoolId) ?? []), ...(teachers.data?.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）`, school_id: schoolId })) ?? [])]
    .filter((value, index, values) => values.findIndex(other => other.id === value.id) === index)
  const teacherId = teacherChoice && candidates.some(value => value.id === teacherChoice) ? teacherChoice : candidates.find(value => value.id === page.user.id)?.id ?? candidates[0]?.id ?? ""
  const base = page.session.workRole === "administrator" ? "/administration" : "/teaching"
  function refresh() { catalogs.reload(); classes.reload(); context.reload() }
  function resetPicker() { setTeacherQ(""); setTeacherTerm(""); setTeacherChoice(""); setCollegeChoice("") }
  return <BusinessPage page={page} title={page.session.workRole === "administrator" ? "课程与教学班管理" : "我的课程与教学班"} description="课程目录组织共享资源，教学班分别管理名单、教师与考核。">
    <ActionFeedback action={action} />
    <div className="b1-actions"><button className="b1-button" type="button" onClick={() => { setShowCreate(true); setSelectedCatalog(null); setEditingCatalog(null); setCreated(null); resetPicker() }}>新建课程与首班</button><button className="b1-button b1-secondary" type="button" onClick={refresh}>刷新课程数据</button></div>
    <Section title="查找课程与教学班">
      <form className="b1-filter" onSubmit={event => { event.preventDefault(); setQ(term.trim()); setClassOffset(0); setCatalogOffset(0) }}>
        <Field label="名称或代码"><input value={term} onChange={event => setTerm(event.target.value)} maxLength={100} placeholder="输入课程或教学班关键词" /></Field>
        <Field label="开课状态"><select value={String(archived)} onChange={event => { setArchived(event.target.value === "true"); setClassOffset(0); setCatalogOffset(0) }}><option value="false">当前开课</option><option value="true">归档历史</option></select></Field>
        <button className="b1-button">查询课程</button><button className="b1-button b1-secondary" type="button" onClick={() => { setQ(""); setTerm(""); setCatalogFilter(""); setClassOffset(0); setCatalogOffset(0) }}>清空查询</button>
      </form>
    </Section>
    {context.error && <Notice kind="error" retry={context.reload}>{context.error}</Notice>}
    <Section title="课程目录" description="负责人可管理目录及共享资源；目录关系不会自动开放其他班级的名单或成绩。">
      {catalogs.loading ? <Loading /> : catalogs.error ? <Notice kind="error" retry={catalogs.reload}>{catalogs.error}</Notice> : catalogs.data?.count === 0 ? <Empty>当前授权范围内没有匹配的课程目录。</Empty> : catalogs.data && <>
        <div className="b1-card-grid">{catalogs.data.data.map(row => <article className="b1-card" key={row.id}><Badge muted={row.archived}>{row.archived ? "归档目录" : "课程目录"}</Badge>{row.owner_id === page.user.id && <Badge>本人负责</Badge>}<h3>{row.title}</h3><p>目录代码：{row.code}</p><div className="b1-actions">
          <button className="b1-button b1-secondary" type="button" onClick={() => { setCatalogFilter(row.id); setClassOffset(0); setQ(""); setTerm("") }}>查看本目录教学班</button>
          {canManageCatalog(page, row) && <><button className="b1-button b1-secondary" type="button" disabled={row.archived} onClick={() => { setSelectedCatalog(row); setEditingCatalog(null); setShowCreate(true); setCreated(null); resetPicker() }}>在此目录开班</button><button className="b1-button b1-secondary" type="button" onClick={() => { setEditingCatalog(row); setSelectedCatalog(null); setShowCreate(false); resetPicker() }}>编辑目录</button></>}
        </div></article>)}</div><Pager offset={catalogOffset} count={catalogs.data.count} change={setCatalogOffset} />
      </>}
    </Section>
    <Section title="有权访问的教学班" description={catalogFilter ? "当前按所选目录筛选，班级权限仍独立验证。" : "显示当前身份获授权的教学班。"} actions={catalogFilter ? <button className="b1-button b1-secondary" onClick={() => { setCatalogFilter(""); setClassOffset(0) }}>显示全部授权班级</button> : undefined}>
      {classes.loading ? <Loading /> : classes.error ? <Notice kind="error" retry={classes.reload}>{classes.error}</Notice> : classes.data?.count === 0 ? <Empty>当前条件下没有获授权教学班。</Empty> : classes.data && <>
        <div className="b1-card-grid">{classes.data.data.map(row => <article className="b1-card" key={row.id}><Badge muted={archived}>{archived ? "历史班级" : "教学班"} · {row.code}</Badge><h3>{row.title}</h3><p>{row.college_name} · 主教师 {row.teacher_name}</p><div className="b1-actions"><button className="b1-button" onClick={() => page.navigate(`${base}/classes/${row.id}`)}>{archived ? "查看班级历史" : "管理教学班"}</button></div></article>)}</div><Pager offset={classOffset} count={classes.data.count} change={setClassOffset} />
      </>}
    </Section>
    {showCreate && <Section title={selectedCatalog ? `已有课程开班：${selectedCatalog.title}` : "新建课程目录与首班"} description={selectedCatalog ? "目录和本班分别授权；负责人可以指定主教师，跨学院开班由校管理员协调。" : "创建同名目录与首班，之后可以分别修改目录和教学班名称。"} actions={<button className="b1-button b1-secondary" onClick={() => setShowCreate(false)}>收起开班表单</button>}>
      {context.loading ? <Loading /> : <form className="b1-form" onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body: CourseCreate = { college_id: collegeId, teacher_id: teacherId, code: input(form, "code"), title: input(form, "title"), ...(selectedCatalog ? { catalog_id: selectedCatalog.id } : {}) }
        void action.run(async key => (await CoursesService.createCourse({ body, headers: commandHeaders(key) })).data,
          result => { form.reset(); setCreated({ course: result, assignedToSelf: page.session.workRole === "administrator" || teacherId === page.user.id }); setShowCreate(false); setQ(""); setTerm(""); setClassOffset(0); refresh() }, "课程 / 教学班已创建", JSON.stringify(["class-create", body]))
      }}>
        <Field label="开班学院"><select value={collegeId} required onChange={event => { setCollegeChoice(event.target.value); setTeacherChoice("") }}><Options values={colleges} /></select></Field>
        <Field label="主教师"><select value={teacherId} required onChange={event => setTeacherChoice(event.target.value)}><Options values={candidates} /></select></Field>
        <Field label={selectedCatalog ? "教学班代码" : "目录与首班代码"}><input name="code" required pattern="[A-Za-z0-9_\-]+" maxLength={40} /></Field>
        <Field label={selectedCatalog ? "教学班名称" : "课程与首班名称"}><input name="title" required maxLength={120} /></Field>
        <div className="b1-wide b1-actions"><button className="b1-button" disabled={action.pending || !collegeId || !teacherId}>{action.pending ? "正在创建…" : "确认创建教学班"}</button></div>
      </form>}
    </Section>}
    {editingCatalog && <Section title={`编辑课程目录：${editingCatalog.title}`} description="课程信息与教学班分别保存；有活动班级时不能直接归档目录。">
      <form className="b1-form" key={`${editingCatalog.id}:${editingCatalog.revision}`} onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body = { revision: editingCatalog.revision, title: input(form, "title"), archived: input(form, "archived") === "true", ...(page.session.workRole === "administrator" && teacherChoice ? { owner_id: teacherChoice } : {}) }
        void action.run(async key => (await TeachingService.updateCatalog({ path: { catalog_id: editingCatalog.id }, body, headers: commandHeaders(key) })).data,
          () => { setEditingCatalog(null); refresh() }, "课程目录已更新", JSON.stringify(["catalog-update", editingCatalog.id, body]))
      }}><Field label="课程目录名称"><input name="title" required maxLength={120} defaultValue={editingCatalog.title} /></Field><Field label="目录状态"><select name="archived" defaultValue={String(editingCatalog.archived)}><option value="false">使用中</option><option value="true">归档</option></select></Field>
        {page.session.workRole === "administrator" && <Field label="新负责人（不选择则保持）"><select value={teacherChoice} onChange={event => setTeacherChoice(event.target.value)}><Options values={teachers.data?.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` })) ?? []} empty="保持当前负责人" /></select></Field>}
        <div className="b1-wide b1-actions"><button className="b1-button" disabled={action.pending}>保存课程目录</button><button className="b1-button b1-secondary" type="button" onClick={() => setEditingCatalog(null)}>取消编辑</button></div>
      </form>
    </Section>}
    {pickerCatalog && (showCreate || (editingCatalog && page.session.workRole === "administrator")) && <Section title="查找课程可指定的本校教师" description="只返回教师账号、姓名和学院等最小选择信息。">
      <form className="b1-filter" onSubmit={event => { event.preventDefault(); setTeacherQ(teacherTerm.trim()); setTeacherChoice("") }}><Field label="教师姓名或账号"><input value={teacherTerm} onChange={event => setTeacherTerm(event.target.value)} required minLength={2} maxLength={100} placeholder="至少输入2个字" /></Field><button className="b1-button b1-secondary">查找可指定教师</button></form>
      {teachers.loading && <Loading />}{teachers.error && <Notice kind="error" retry={teachers.reload}>{teachers.error}</Notice>}{teachers.data?.count === 0 && <Empty>没有匹配的本校教师。</Empty>}
      {teachers.data && teachers.data.count > 0 && <Field label="指定查找到的教师"><select value={teacherChoice} onChange={event => setTeacherChoice(event.target.value)}><Options values={teachers.data.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` }))} /></select></Field>}
    </Section>}
    {created && <Notice kind="success"><strong>{created.course.title} 已建立。</strong>{created.assignedToSelf ? <button type="button" className="b1-button b1-secondary" onClick={() => page.navigate(`${base}/classes/${created.course.id}`)}>进入新教学班</button> : <span>班级由指定主教师管理；目录负责人不会自动获得该班名单、成绩或私有资料权限。</span>}</Notice>}
    <Notice>课件、题库与共享版本由 C 接入；正式考试和培训记录由 B2 接入。当前目录不代表已有共享课件。</Notice>
  </BusinessPage>
}
