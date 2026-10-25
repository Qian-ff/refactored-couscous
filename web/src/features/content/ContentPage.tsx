import { useCallback, useState } from "react"
import { ContentService, type VersionView, type LibraryView, type ReviewView, type contentListMaterialsData } from "../../client"
import type { PageProps, PageRegistration } from "../../lib/extensions"
import { sessionSnapshot } from "../../lib/api"
import { Button, Field, Notice, Pagination, Panel, RecordList, StatePanel } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import { MaterialPublish, MaterialReview, MaterialWorkspace, type MaterialItem, type MaterialWorkspaceProps } from "./ContentWorkspace"
import { materialItem } from "./material-adapter"
import { ContentPreview, ContentUpload, ContentEdit, ContentSubmit, TextMaterial } from "./ContentDialogs"
import { LibraryCreate } from "./LibraryCreate"
import { CourseSelector, LibraryBrowser } from "./ScopeSelectors"

const emptyFilters = { course: "", courseLabel: "", fileType: "", after: "", before: "" }

export function ContentPage({ session, platform }: PageProps) {
  const student = session.workRole === "student"
  const [query, setQuery] = useState(""), [library, setLibrary] = useState(""), [offset, setOffset] = useState(0), [round, setRound] = useState(0)
  const [filters, setFilters] = useState(emptyFilters), [applied, setApplied] = useState(emptyFilters), [jobOffset, setJobOffset] = useState(0), [scopeLibrary, setScopeLibrary] = useState<LibraryView>()
  const [jobVersion, setJobVersion] = useState(""), [jobVersionLabel, setJobVersionLabel] = useState("")
  const [dialog, setDialog] = useState<"upload" | "text" | "preview" | "edit" | "submit" | "review" | "publish" | "libraries" | "create-library" | "scope">()
  const [uploadVersion, setUploadVersion] = useState<VersionView>()
  const [selected, setSelected] = useState<VersionView>(), [review, setReview] = useState<ReviewView>(), [editingLibrary, setEditingLibrary] = useState<LibraryView>()
  const [notice, setNotice] = useState("")
  const libraries = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.listLibraries({ query: { limit: 20, include_inactive: !student }, signal })).data, [student, round]))
  const targets = useResource(useCallback(async (signal: AbortSignal) => student ? [] : (await ContentService.submitTargets({ query: { limit: 20 }, signal })).data, [student, round]))
  const capabilities = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.capabilities({ signal })).data, [round]))
  const materials = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.listMaterials({ query: { q: query, library_id: library || undefined, offset, limit: 20,
    course_id: applied.course || undefined, file_type: (applied.fileType || undefined) as NonNullable<contentListMaterialsData["query"]>["file_type"],
    created_after: applied.after ? new Date(applied.after).toISOString() : undefined, created_before: applied.before ? new Date(applied.before).toISOString() : undefined }, signal })).data, [query, library, offset, round, applied]))
  const jobs = useResource(useCallback(async (signal: AbortSignal) => student ? undefined : (await ContentService.listJobs({ query: { offset: jobOffset, limit: 20, version_id: jobVersion || undefined }, signal })).data, [student, round, jobOffset, jobVersion]))
  const action = useCommand()
  const refresh = () => { setNotice(""); setRound(value => value + 1) }
  const done = (message: string, version?: { id: string; title: string }) => { setDialog(undefined); setSelected(undefined); setReview(undefined); setEditingLibrary(undefined); setNotice(message); setJobOffset(0); if (version) { setJobVersion(version.id); setJobVersionLabel(version.title) }; setRound(value => value + 1) }
  const names = new Map((libraries.data?.items || []).map(row => [row.id, row.title]))
  if (scopeLibrary) names.set(scopeLibrary.id, scopeLibrary.title)
  const scopeNames = (libraries.data?.items || []).map(row => ({ id: row.id, label: row.title }))
  if (scopeLibrary && !scopeNames.some(row => row.id === scopeLibrary.id)) scopeNames.push({ id: scopeLibrary.id, label: scopeLibrary.title })
  const uploads = (targets.data || []).map(row => ({ id: row.id, label: row.title }))
  const state = materials.loading ? "loading" : materials.error ? materials.status === 403 ? "forbidden" : materials.status === 404 ? "unavailable" : navigator.onLine ? "error" : "offline" : "ready"
  const sourceItems = materials.data?.items || []
  const targetId = (version: VersionView) => version.binding?.target_library_id || version.library_id
  function choose(kind: Parameters<MaterialWorkspaceProps["onAction"]>[0], item: MaterialItem) {
    const version = sourceItems.find(row => row.version_id === item.versionId && targetId(row) === item.targetLibraryId)
    if (!version) return
    action.clear(); setNotice(""); setSelected(version)
    if (kind === "download") { void download(version); return }
    if (kind === "review" || kind === "publish") { setReview(version.binding?.review || undefined); setDialog(kind); return }
    setDialog(kind)
  }
  async function download(version: VersionView) {
    const response = await action.run("download:" + version.version_id + ":" + targetId(version), async () => {
      const generation = sessionSnapshot().generation
      const result = await ContentService.downloadVersion({ path: { version_id: version.version_id }, query: { library_id: targetId(version) } })
      if (generation !== sessionSnapshot().generation) throw new Error("工作身份已改变，请重新打开资料")
      const url = URL.createObjectURL(result.data), anchor = document.createElement("a")
      anchor.href = url; anchor.download = (version.original_name || version.title + ".txt").replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_")
      anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
      return result
    })
    if (response) setNotice(platform.kind === "web" ? "下载已开始，请在浏览器下载列表核对结果。" : "已取得原件并发起下载，请核对设备下载结果。客户端保存功能尚待原生接入。")
  }
  return <div className="lc-content-product">
    {notice && <Notice>{notice}</Notice>}{action.error && <Notice kind="error">{action.error}</Notice>}
    <MaterialWorkspace audience={student ? "student" : "staff"} state={state} error={materials.error} items={sourceItems.map(version => materialItem(version, names.get(targetId(version)) || "当前授权范围"))}
      total={materials.data?.total || 0} offset={offset} pageSize={20} query={query} libraryId={library} libraries={scopeNames}
      canUpload={!student && uploads.length > 0 && !!capabilities.data?.storage_available && !!capabilities.data?.parser_available}
      canManageLibrary={!student && (libraries.data?.items.some(row => row.can_manage) || !!scopeLibrary?.can_manage)} searchPlaceholder="标题、文件名、正文或输入知识点文字"
      hasFilters={!!(applied.course || applied.fileType || applied.after || applied.before)}
      scopeNotice="只检索当前授权范围。正文命中来自已提取快照；输入知识点文字不等于题库标签。仅chunk命中提供真实页段定位，标题/文件名/未提取输入文字不补造定位。"
      filterControls={<><Button variant="secondary" onClick={() => setDialog("scope")}>查找更多资料范围</Button><details className="lc-content-filters"><summary>课程、类型与版本时间筛选</summary>
        <CourseSelector value={filters.course} label={filters.courseLabel} onChange={(id, label) => setFilters(current => ({ ...current, course: id, courseLabel: label }))} />
        <div className="lc-content-filter-fields"><Field label="资料类型"><select value={filters.fileType} onChange={e => setFilters(current => ({ ...current, fileType: e.target.value }))}><option value="">全部类型</option><option value="pdf">PDF</option><option value="pptx">PPTX</option><option value="docx">DOCX</option><option value="txt">TXT文件</option><option value="text">输入知识点文字</option></select></Field>
          <Field label="版本创建起始时间（本机时间）"><input type="datetime-local" value={filters.after} max={filters.before || undefined} onChange={e => setFilters(current => ({ ...current, after: e.target.value }))} /></Field>
          <Field label="版本创建截止时间（本机时间）"><input type="datetime-local" value={filters.before} min={filters.after || undefined} onChange={e => setFilters(current => ({ ...current, before: e.target.value }))} /></Field></div><p>筛选的是版本创建时间；不会当作资料名称修改时间。选择后点击搜索生效。</p>
      </details></>}
      onClear={() => { setQuery(""); setLibrary(""); setScopeLibrary(undefined); setFilters(emptyFilters); setApplied(emptyFilters); setOffset(0) }}
      onSearch={(text, id) => { setQuery(text); setLibrary(id); setApplied({ ...filters }); setOffset(0) }} onPage={setOffset} onRefresh={refresh} onUpload={() => { setUploadVersion(undefined); setDialog("upload") }} onManageLibrary={() => setDialog("libraries")} onJobs={item => { setJobVersion(item.versionId); setJobVersionLabel(item.title); setJobOffset(0) }} onAction={choose} />
    {!student && <Panel title="资料处理与提交">
      <Button variant="secondary" onClick={() => setDialog("create-library")}>新建资料库</Button>
      <Button variant="secondary" onClick={() => setDialog("libraries")}>查找资料库与管理权限</Button>
      {targets.error && <Notice kind="error" retry={targets.reload}>{targets.error}</Notice>}
      {capabilities.error && <Notice kind="error" retry={capabilities.reload}>{capabilities.error}</Notice>}
      {capabilities.data && (!capabilities.data.parser_available || !capabilities.data.storage_available) && <Notice kind="warning">{!capabilities.data.parser_available ? "解析服务尚未就绪。" : ""}{!capabilities.data.storage_available ? "资料存储尚未配置。" : ""}当前不能上传解析文件。</Notice>}
      {uploads.length > 0 && <Button variant="secondary" onClick={() => setDialog("text")}>录入知识点文字</Button>}
      {jobVersion && <Notice>当前查看：{jobVersionLabel}<Button variant="secondary" onClick={() => { setJobVersion(""); setJobVersionLabel(""); setJobOffset(0) }}>查看全部本人任务</Button></Notice>}
      {jobs.loading ? <StatePanel kind="loading" /> : jobs.error ? <StatePanel kind="error" description={jobs.error} retry={jobs.reload} /> : jobs.data?.items.length ? <RecordList items={jobs.data.items} itemKey={row => row.job_id} title={row => "解析任务：" + (sourceItems.find(version => version.version_id === row.version_id)?.title || (jobVersion === row.version_id ? jobVersionLabel : "关联资料"))}
        fields={[{ label: "状态", value: row => ({ queued: "排队中", running: "解析中", succeeded: "解析完成", failed: "解析失败", canceled: "已取消" } as Record<string, string>)[row.state] || row.state }, { label: "阶段", value: row => row.stage }, { label: "错误", value: row => row.error_code || "无" }]}
        actions={row => <><Button variant="secondary" pending={action.pending} onClick={async () => {
          const result = await action.run("job-version:" + row.version_id, () => ContentService.versionDetail({ path: { version_id: row.version_id } }))
          if (result?.data.actions?.preview) { setSelected(result.data); setDialog("preview") }
          else if (result) setNotice(result.data.title + "：当前尚无可预览正文，请核对解析任务状态。")
        }}>查看任务资料</Button>{["queued", "running"].includes(row.state) && <Button variant="secondary" pending={action.pending} onClick={async () => { const result = await action.run("cancel-job:" + row.job_id, key => ContentService.cancelJob({ path: { job_id: row.job_id }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认取消解析任务。") }}>取消解析</Button>}{["failed", "canceled"].includes(row.state) && <Button variant="secondary" pending={action.pending} onClick={async () => { const result = await action.run("retry-job:" + row.job_id, key => ContentService.retryJob({ path: { job_id: row.job_id }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已接收重试任务，请刷新读取实际状态。") }}>重试解析</Button>}</>} /> : <p>{jobVersion ? "暂无这个版本的本人解析任务。" : "暂无本人解析任务。"}</p>}
      {jobs.data && <Pagination total={jobs.data.total} offset={jobOffset} pageSize={20} onChange={setJobOffset} />}
      <p>任务状态来自服务器；点击“刷新资料”可重新读取。已发布资料的阅读权限不授予草稿编辑或整库管理权。</p>
    </Panel>}
    {dialog === "preview" && selected && <ContentPreview version={selected} onClose={() => setDialog(undefined)} onDownload={() => { void download(selected) }} />}
    {dialog === "upload" && <ContentUpload version={uploadVersion} targets={uploads} capabilities={capabilities.data} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "text" && <TextMaterial targets={uploads} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "edit" && selected && <ContentEdit version={selected} onClose={() => setDialog(undefined)} onDone={done} onNewVersion={version => { setUploadVersion(version); setDialog("upload") }} />}
    {dialog === "submit" && selected && <ContentSubmit version={selected} targetLabel={names.get(targetId(selected)) || "当前授权范围"} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "review" && selected && review && <MaterialReview key={review.id} title={selected.title} versionLabel={`第 ${selected.version_no} 版 · ${names.get(review.target_library_id) || review.target_library_id}`} authorization={review.authorization_statement} warnings={selected.warnings} pending={action.pending} error={action.error}
      onClose={() => setDialog(undefined)} onConfirm={async input => { const result = await action.run("review:" + review.id + JSON.stringify(input), key => ContentService.decideReview({ path: { review_id: review.id }, body: { revision: review.revision, decision: input.decision, reason: input.reason || null, warning_hash: review.warning_hash, warnings_acknowledged: input.warningsAcknowledged, original_authorized: input.originalAuthorized }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认审核决定，尚未执行发布。") }} />}
    {dialog === "publish" && selected && review && <MaterialPublish title={selected.title} versionLabel={`第 ${selected.version_no} 版`} targetLabel={names.get(review.target_library_id) || review.target_library_id} pending={action.pending} error={action.error} onClose={() => setDialog(undefined)} onConfirm={async () => {
      const result = await action.run("publish:" + review.id + ":" + review.revision, key => ContentService.publishReview({ body: { review_id: review.id, revision: review.revision }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认向指定范围发布该版本。")
    }} />}
    {dialog === "libraries" && !editingLibrary && <LibraryBrowser includeInactive={!student} onEdit={setEditingLibrary} onClose={() => setDialog(undefined)} />}
    {dialog === "scope" && <LibraryBrowser includeInactive={false} onChoose={row => { setScopeLibrary(row); setLibrary(row.id); setOffset(0); setDialog(undefined) }} onClose={() => setDialog(undefined)} />}
    {dialog === "libraries" && editingLibrary && <ContentEdit library={editingLibrary} onClose={() => { setEditingLibrary(undefined); setDialog(undefined) }} onDone={done} />}
    {dialog === "create-library" && <LibraryCreate user={session.user!} onClose={() => setDialog(undefined)} onDone={done} />}
  </div>
}
export const contentPages: readonly PageRegistration[] = [
  { id: "d-content-materials", path: "/content/materials", title: "资料中心", workRoles: ["student", "teacher", "administrator"], component: ContentPage, navGroup: "content" },
]
