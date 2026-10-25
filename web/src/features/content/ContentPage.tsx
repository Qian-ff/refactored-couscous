import { useCallback, useState } from "react"
import { ContentService, type VersionView, type LibraryView, type ReviewView } from "../../client"
import type { PageProps, PageRegistration } from "../../lib/extensions"
import { sessionSnapshot } from "../../lib/api"
import { Button, Notice, Panel, RecordList, StatePanel } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import { MaterialPublish, MaterialReview, MaterialWorkspace, type MaterialItem, type MaterialWorkspaceProps } from "./ContentWorkspace"
import { materialItem } from "./material-adapter"
import { ContentPreview, ContentUpload, ContentEdit, ContentSubmit, LibraryEdit, TextMaterial } from "./ContentDialogs"
import { LibraryCreate } from "./LibraryCreate"

export function ContentPage({ session }: PageProps) {
  const student = session.workRole === "student"
  const [query, setQuery] = useState(""), [library, setLibrary] = useState(""), [offset, setOffset] = useState(0), [round, setRound] = useState(0)
  const [dialog, setDialog] = useState<"upload" | "text" | "preview" | "edit" | "submit" | "review" | "publish" | "libraries" | "create-library">()
  const [uploadVersion, setUploadVersion] = useState<VersionView>()
  const [selected, setSelected] = useState<VersionView>(), [review, setReview] = useState<ReviewView>(), [editingLibrary, setEditingLibrary] = useState<LibraryView>()
  const [notice, setNotice] = useState("")
  const libraries = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.listLibraries({ query: { limit: 100, include_inactive: !student }, signal })).data, [student, round]))
  const targets = useResource(useCallback(async (signal: AbortSignal) => student ? [] : (await ContentService.submitTargets({ query: { limit: 100 }, signal })).data, [student, round]))
  const capabilities = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.capabilities({ signal })).data, [round]))
  const materials = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.listMaterials({ query: { q: query, library_id: library || undefined, offset, limit: 20 }, signal })).data, [query, library, offset, round]))
  const jobs = useResource(useCallback(async (signal: AbortSignal) => student ? undefined : (await ContentService.listJobs({ query: { limit: 20 }, signal })).data, [student, round]))
  const action = useCommand()
  const refresh = () => { setNotice(""); setRound(value => value + 1) }
  const done = (message: string) => { setDialog(undefined); setSelected(undefined); setReview(undefined); setEditingLibrary(undefined); setNotice(message); setRound(value => value + 1) }
  const names = new Map((libraries.data?.items || []).map(row => [row.id, row.title]))
  const scopeNames = (libraries.data?.items || []).map(row => ({ id: row.id, label: row.title }))
  const uploads = (targets.data || []).map(row => ({ id: row.id, label: row.title }))
  const state = materials.loading ? "loading" : materials.error ? materials.status === 403 ? "forbidden" : [404, 503].includes(materials.status || 0) ? "unavailable" : navigator.onLine ? "error" : "offline" : "ready"
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
    if (response) setNotice("原件已交给浏览器下载；保存位置由浏览器或客户端决定。")
  }
  return <div className="lc-content-product">
    {notice && <Notice>{notice}</Notice>}{action.error && <Notice kind="error">{action.error}</Notice>}
    <MaterialWorkspace audience={student ? "student" : "staff"} state={state} error={materials.error} items={sourceItems.map(version => materialItem(version, names.get(targetId(version)) || "当前授权范围"))}
      total={materials.data?.total || 0} offset={offset} pageSize={20} query={query} libraryId={library} libraries={scopeNames}
      canUpload={!student && uploads.length > 0 && !!capabilities.data?.storage_available && !!capabilities.data?.parser_available}
      canManageLibrary={!student && (libraries.data?.items.some(row => row.can_manage) || false)} searchPlaceholder="资料标题或原文件名"
      scopeNotice="当前搜索匹配标题和文件名；正文、知识点匹配尚未接通。选择具体范围后，审核与发布状态仅针对该目标；定位预览和下载会重新校验权限。"
      onSearch={(text, id) => { setQuery(text); setLibrary(id); setOffset(0) }} onPage={setOffset} onRefresh={refresh} onUpload={() => { setUploadVersion(undefined); setDialog("upload") }} onManageLibrary={() => setDialog("libraries")} onAction={choose} />
    {!student && <Panel title="资料处理与提交">
      <Button variant="secondary" onClick={() => setDialog("create-library")}>新建资料库</Button>
      {targets.error && <Notice kind="error" retry={targets.reload}>{targets.error}</Notice>}
      {capabilities.error && <Notice kind="error" retry={capabilities.reload}>{capabilities.error}</Notice>}
      {capabilities.data && (!capabilities.data.parser_available || !capabilities.data.storage_available) && <Notice kind="warning">{!capabilities.data.parser_available ? "解析服务尚未就绪。" : ""}{!capabilities.data.storage_available ? "资料存储尚未配置。" : ""}当前不能上传解析文件。</Notice>}
      {uploads.length > 0 && <Button variant="secondary" onClick={() => setDialog("text")}>录入知识点文字</Button>}
      {jobs.loading ? <StatePanel kind="loading" /> : jobs.error ? <StatePanel kind="error" description={jobs.error} retry={jobs.reload} /> : jobs.data?.items.length ? <RecordList items={jobs.data.items} itemKey={row => row.job_id} title={row => "解析任务 · " + row.version_id}
        fields={[{ label: "状态", value: row => ({ queued: "排队中", running: "解析中", succeeded: "解析完成", failed: "解析失败", canceled: "已取消" } as Record<string, string>)[row.state] || row.state }, { label: "阶段", value: row => row.stage }, { label: "错误", value: row => row.error_code || "无" }]}
        actions={row => <>{["queued", "running"].includes(row.state) && <Button variant="secondary" pending={action.pending} onClick={async () => { const result = await action.run("cancel-job:" + row.job_id, key => ContentService.cancelJob({ path: { job_id: row.job_id }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认取消解析任务。") }}>取消解析</Button>}{["failed", "canceled"].includes(row.state) && <Button variant="secondary" pending={action.pending} onClick={async () => { const result = await action.run("retry-job:" + row.job_id, key => ContentService.retryJob({ path: { job_id: row.job_id }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已接收重试任务，请刷新读取实际状态。") }}>重试解析</Button>}</>} /> : <p>暂无本人解析任务。</p>}
      <p>任务状态来自服务器；点击“刷新资料”可重新读取。已发布资料的阅读权限不授予草稿编辑或整库管理权。</p>
    </Panel>}
    {dialog === "preview" && selected && <ContentPreview version={selected} onClose={() => setDialog(undefined)} onDownload={() => { void download(selected) }} />}
    {dialog === "upload" && <ContentUpload version={uploadVersion} targets={uploads} capabilities={capabilities.data} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "text" && <TextMaterial targets={uploads} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "edit" && selected && <ContentEdit version={selected} onClose={() => setDialog(undefined)} onDone={done} onNewVersion={version => { setUploadVersion(version); setDialog("upload") }} />}
    {dialog === "submit" && selected && <ContentSubmit version={selected} targets={uploads} targetLabel={names.get(targetId(selected)) || "当前授权范围"} onClose={() => setDialog(undefined)} onDone={done} />}
    {dialog === "review" && selected && review && <MaterialReview key={review.id} title={selected.title} versionLabel={`第 ${selected.version_no} 版 · ${names.get(review.target_library_id) || review.target_library_id}`} authorization={review.authorization_statement} warnings={selected.warnings} pending={action.pending} error={action.error}
      onClose={() => setDialog(undefined)} onConfirm={async input => { const result = await action.run("review:" + review.id + JSON.stringify(input), key => ContentService.decideReview({ path: { review_id: review.id }, body: { revision: review.revision, decision: input.decision, reason: input.reason || null, warning_hash: review.warning_hash, warnings_acknowledged: input.warningsAcknowledged, original_authorized: input.originalAuthorized }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认审核决定，尚未执行发布。") }} />}
    {dialog === "publish" && selected && review && <MaterialPublish title={selected.title} versionLabel={`第 ${selected.version_no} 版`} targetLabel={names.get(review.target_library_id) || review.target_library_id} pending={action.pending} error={action.error} onClose={() => setDialog(undefined)} onConfirm={async () => {
      const result = await action.run("publish:" + review.id + ":" + review.revision, key => ContentService.publishReview({ body: { review_id: review.id, revision: review.revision }, headers: { "Idempotency-Key": key } })); if (result) done("服务端已确认向指定范围发布该版本。")
    }} />}
    {dialog === "libraries" && !editingLibrary && <LibraryEdit libraries={libraries.data?.items.filter(row => row.can_manage) || []} onSelect={setEditingLibrary} onClose={() => setDialog(undefined)} />}
    {dialog === "libraries" && editingLibrary && <ContentEdit library={editingLibrary} onClose={() => { setEditingLibrary(undefined); setDialog(undefined) }} onDone={done} />}
    {dialog === "create-library" && <LibraryCreate user={session.user!} onClose={() => setDialog(undefined)} onDone={done} />}
  </div>
}
export const contentPages: readonly PageRegistration[] = [
  { id: "d-content-materials", path: "/content/materials", title: "资料中心", workRoles: ["student", "teacher", "administrator"], component: ContentPage, navGroup: "content" },
]
