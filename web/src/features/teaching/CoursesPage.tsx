import { useCallback, useState } from "react"
import { CoursesService, TeachingService, type CatalogView, type CourseCreate, type CoursePublic } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { Options } from "../admin/forms"
import { canManageCatalog, isSchoolManager } from "../admin/scope"
import { FilterFields, BusinessRecords, EditorDialog, SearchFilters, Button, ActionFeedback, Badge, BusinessPage, commandHeaders, Empty, Field, input, Loading, Notice, Pager, Section, SessionPage, useBusinessAction, useBusinessQuery } from "./ui"

export function CoursesPage(page: PageProps) { return <SessionPage page={page}><CoursesBody {...page} /></SessionPage> }
function CoursesBody(page: PageProps) {
  const [term, setTerm] = useState("")
  const [catalogTerm, setCatalogTerm] = useState("")
  const [catalogQ, setCatalogQ] = useState("")
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
  const catalogs = useBusinessQuery(page.session, useCallback(async signal => (await TeachingService.catalogs({ query: { q: catalogQ, archived, offset: catalogOffset, limit: 20 }, signal })).data, [catalogQ, archived, catalogOffset]))
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
  return <BusinessPage page={page} title={page.session.workRole === "administrator" ? "课程与教学班管理" : "我的课程与教学班"} description="先选课程目录，再按独立授权管理教学班。">
    {!showCreate && !editingCatalog && <ActionFeedback action={action} />}
    <div className="b1-task-bar"><Button variant="secondary" onClick={refresh}>刷新课程数据</Button><Button onClick={() => { setShowCreate(true); setSelectedCatalog(null); setEditingCatalog(null); setCreated(null); resetPicker() }}>新建课程与首班</Button></div>
    {context.error && <Notice kind="error" retry={context.reload}>{context.error}</Notice>}
    <div className="b1-course-workspace">
      <aside className="b1-catalog-index"><details className="b1-directory" open><summary>课程目录与全部授权班级</summary>
        <Section title="课程目录" description="目录组织共享资料，各班级的名单和考核独立授权。">
          <SearchFilters label="目录名称或代码" placeholder="查找课程目录" value={catalogTerm} onChange={setCatalogTerm} onSearch={() => { setCatalogQ(catalogTerm.trim()); setCatalogOffset(0) }} onClear={() => { setCatalogTerm(""); setCatalogQ(""); setCatalogOffset(0) }} />
          <Button variant={catalogFilter ? "secondary" : "primary"} onClick={() => { setCatalogFilter(""); setClassOffset(0) }}>全部授权班级</Button>
          {catalogs.loading ? <Loading /> : catalogs.error ? <Notice kind="error" retry={catalogs.reload}>{catalogs.error}</Notice> : catalogs.data?.count === 0 ? <Empty>当前授权范围内没有匹配的课程目录。</Empty> : catalogs.data && <>
            <div className="b1-catalog-scroll">{catalogs.data.data.map(row => <article className={`b1-catalog-item ${catalogFilter === row.id ? "b1-selected" : ""}`} key={row.id}>
              <h3><Button variant="quiet" onClick={() => { setCatalogFilter(row.id); setClassOffset(0); setQ(""); setTerm("") }}>{row.title}</Button></h3><p>目录代码：{row.code}</p><Badge muted={row.archived}>{row.archived ? "归档目录" : "在用目录"}</Badge>{row.owner_id === page.user.id && <Badge>本人所有</Badge>}
              <div className="b1-actions"><Button variant="secondary" onClick={() => { setCatalogFilter(row.id); setClassOffset(0); setQ(""); setTerm("") }}>查看本目录教学班</Button>
                {canManageCatalog(page, row) && <><Button variant="secondary" disabled={row.archived} onClick={() => { setSelectedCatalog(row); setEditingCatalog(null); setShowCreate(true); setCreated(null); resetPicker() }}>在此目录开班</Button><Button variant="secondary" onClick={() => { setEditingCatalog(row); setSelectedCatalog(null); setShowCreate(false); resetPicker() }}>编辑目录</Button></>}
              </div></article>)}</div><Pager offset={catalogOffset} count={catalogs.data.count} change={setCatalogOffset} />
          </>}
        </Section>
      </details></aside>
      <div className="b1-class-workspace"><Section title="有权访问的教学班" description={catalogFilter ? "当前按所选目录筛选；班级权限仍独立验证。" : "当前显示全部获授权教学班。"} actions={catalogFilter ? <Button variant="secondary" onClick={() => { setCatalogFilter(""); setClassOffset(0) }}>显示全部授权班级</Button> : undefined}>
        <SearchFilters label="名称或代码" placeholder="查找教学班" value={term} onChange={setTerm} onSearch={() => { setQ(term.trim()); setClassOffset(0) }} onClear={() => { setQ(""); setTerm(""); setCatalogFilter(""); setClassOffset(0) }}><FilterFields>
          <Field label="开课状态"><select value={String(archived)} onChange={event => { setArchived(event.target.value === "true"); setClassOffset(0); setCatalogOffset(0) }}><option value="false">当前开课</option><option value="true">归档历史</option></select></Field>
        </FilterFields></SearchFilters>
        {classes.loading ? <Loading /> : classes.error ? <Notice kind="error" retry={classes.reload}>{classes.error}</Notice> : classes.data?.count === 0 ? <Empty>当前条件下没有获授权教学班。</Empty> : classes.data && <>
          <BusinessRecords items={classes.data.data} itemKey={row => row.id} titleLabel="教学班" title={row => <span className="b1-record-title"><strong>{row.title}</strong><small>{row.code}</small></span>} fields={[
            { label: "学院", value: row => row.college_name }, { label: "主讲教师", value: row => row.teacher_name }, { label: "状态", value: () => <Badge muted={archived}>{archived ? "历史班级" : "正在开课"}</Badge> },
          ]} actions={row => <Button variant="quiet" onClick={() => page.navigate(`${base}/classes/${row.id}`)}>{archived ? "查看班级历史" : "管理教学班"}</Button>} /><Pager offset={classOffset} count={classes.data.count} change={setClassOffset} />
        </>}
        <p className="b1-inline-note">查看目录不代表可以读取全部教学班；只显示当前身份获授权的班级。</p>
      </Section></div>
    </div>
    {showCreate && <EditorDialog title={selectedCatalog ? `已有课程开班：${selectedCatalog.title}` : "新建课程目录与首班"} pending={action.pending} onClose={() => { setShowCreate(false); resetPicker() }}>
      <ActionFeedback action={action} /><p className="b1-description">{selectedCatalog ? "目录和教学班分别授权。可以指定本校主讲教师，跨学院开班由学校管理员协调。" : "目录与首班初始使用相同代码和名称，之后可以分别维护。"}</p>
      {context.loading ? <Loading /> : <form className="b1-form" onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body: CourseCreate = { college_id: collegeId, teacher_id: teacherId, code: input(form, "code"), title: input(form, "title"), ...(selectedCatalog ? { catalog_id: selectedCatalog.id } : {}) }
        void action.run(async key => (await CoursesService.createCourse({ body, headers: commandHeaders(key) })).data,
          result => { form.reset(); setCreated({ course: result, assignedToSelf: page.session.workRole === "administrator" || teacherId === page.user.id }); setShowCreate(false); setQ(""); setTerm(""); setClassOffset(0); refresh() }, "课程 / 教学班已创建", JSON.stringify(["class-create", body]))
      }}>
        <Field label="开班学院"><select value={collegeId} required onChange={event => { setCollegeChoice(event.target.value); setTeacherChoice("") }}><Options values={colleges} /></select></Field>
        <Field label="主讲教师"><select value={teacherId} required onChange={event => setTeacherChoice(event.target.value)}><Options values={candidates} /></select></Field>
        <Field label={selectedCatalog ? "教学班代码" : "目录与首班代码"}><input name="code" required pattern="[A-Za-z0-9_\-]+" maxLength={40} /></Field>
        <Field label={selectedCatalog ? "教学班名称" : "课程与首班名称"}><input name="title" required maxLength={120} /></Field>
        <div className="b1-wide b1-actions"><Button type="submit"  disabled={action.pending || !collegeId || !teacherId}>{action.pending ? "正在创建…" : "确认创建教学班"}</Button></div>
      </form>}

      {selectedCatalog && <Section title="查找课程可指定的本校教师" description="只返回教师账号、姓名和学院等最小选择信息。">
      <form className="b1-filter" onSubmit={event => { event.preventDefault(); setTeacherQ(teacherTerm.trim()); setTeacherChoice("") }}><Field label="教师姓名或账号"><input value={teacherTerm} onKeyDown={event => { if (event.key === "Enter" && event.nativeEvent.isComposing) event.preventDefault() }} onChange={event => setTeacherTerm(event.target.value)} required minLength={2} maxLength={100} placeholder="至少输入2个字" /></Field><Button type="submit" variant="secondary">查找可指定教师</Button></form>
      {teachers.loading && <Loading />}{teachers.error && <Notice kind="error" retry={teachers.reload}>{teachers.error}</Notice>}{teachers.data?.count === 0 && <Empty>没有匹配的本校教师。</Empty>}
      {teachers.data && teachers.data.count > 0 && <Field label="指定查找到的教师"><select value={teacherChoice} onChange={event => setTeacherChoice(event.target.value)}><Options values={teachers.data.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` }))} /></select></Field>}
    </Section>}
    </EditorDialog>}
    {editingCatalog && <EditorDialog title={`编辑课程目录：${editingCatalog.title}`} pending={action.pending} savedVersion={editingCatalog.revision} onClose={() => { setEditingCatalog(null); resetPicker() }}>
      <ActionFeedback action={action} /><p className="b1-description">代码与归属保持只读；有活动教学班时不能直接归档目录。</p><Field label="目录代码（只读）"><input value={editingCatalog.code} readOnly /></Field>
      {action.error && /修改|冲突|更新/.test(action.error) && <Notice kind="warning">读取最新资料后请重新确认保存。<Button variant="secondary" onClick={() => { void action.run(async () => (await TeachingService.catalog({ path: { catalog_id: editingCatalog.id } })).data, setEditingCatalog, "已读取最新目录资料") }}>读取最新目录资料</Button></Notice>}
      <form className="b1-form" key={`${editingCatalog.id}:${editingCatalog.revision}`} onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget
        const body = { revision: editingCatalog.revision, title: input(form, "title"), archived: input(form, "archived") === "true", ...(page.session.workRole === "administrator" && teacherChoice ? { owner_id: teacherChoice } : {}) }
        void action.run(async key => (await TeachingService.updateCatalog({ path: { catalog_id: editingCatalog.id }, body, headers: commandHeaders(key) })).data,
          () => { setEditingCatalog(null); refresh() }, "课程目录已更新", JSON.stringify(["catalog-update", editingCatalog.id, body]))
      }}><Field label="课程目录名称"><input name="title" required maxLength={120} defaultValue={editingCatalog.title} /></Field><Field label="目录状态"><select name="archived" defaultValue={String(editingCatalog.archived)}><option value="false">使用中</option><option value="true">归档</option></select></Field>
        {page.session.workRole === "administrator" && <Field label="新所有者（不选择则保持）"><select value={teacherChoice} onChange={event => setTeacherChoice(event.target.value)}><Options values={teachers.data?.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` })) ?? []} empty="保持当前所有者" /></select></Field>}
        <div className="b1-wide b1-actions"><Button type="submit"  disabled={action.pending}>保存课程目录</Button><Button variant="secondary" type="button" onClick={() => setEditingCatalog(null)}>取消编辑</Button></div>
      </form>

      {page.session.workRole === "administrator" && <Section title="查找课程可指定的本校教师" description="只返回教师账号、姓名和学院等最小选择信息。">
      <form className="b1-filter" onSubmit={event => { event.preventDefault(); setTeacherQ(teacherTerm.trim()); setTeacherChoice("") }}><Field label="教师姓名或账号"><input value={teacherTerm} onKeyDown={event => { if (event.key === "Enter" && event.nativeEvent.isComposing) event.preventDefault() }} onChange={event => setTeacherTerm(event.target.value)} required minLength={2} maxLength={100} placeholder="至少输入2个字" /></Field><Button type="submit" variant="secondary">查找可指定教师</Button></form>
      {teachers.loading && <Loading />}{teachers.error && <Notice kind="error" retry={teachers.reload}>{teachers.error}</Notice>}{teachers.data?.count === 0 && <Empty>没有匹配的本校教师。</Empty>}
      {teachers.data && teachers.data.count > 0 && <Field label="指定查找到的教师"><select value={teacherChoice} onChange={event => setTeacherChoice(event.target.value)}><Options values={teachers.data.data.map(value => ({ id: value.id, name: `${value.display_name}（${value.username}）` }))} /></select></Field>}
    </Section>}
    </EditorDialog>}
    {created && <Notice kind="success"><strong>{created.course.title} 已建立。</strong>{created.assignedToSelf ? <Button type="button" variant="secondary" onClick={() => page.navigate(`${base}/classes/${created.course.id}`)}>进入新教学班</Button> : <span>班级由指定主讲教师管理；目录所有者不会自动获得该班名单、成绩或私有资料权限。</span>}</Notice>}
    <Notice>课件、题库、正式考试和培训记录暂未开放。共享资料开放后需经审核发布。</Notice>
  </BusinessPage>
}
