import { useEffect, useState, type ReactNode } from "react"
import { Button, Dialog, Field, Notice, PageContainer, Pagination, Panel, RecordList, SearchFilters, StatePanel } from "../../components/labconnect"
import "./content.css"

// Presentation props only. The released generated SDK will supply the production adapter.
export type MaterialItem = Readonly<{
  versionId: string; title: string; originalName: string | null; libraryLabel: string; versionNo: number
  extraction: "queued" | "running" | "succeeded" | "failed" | "canceled"
  publication: "draft" | "submitted" | "approved" | "rejected" | "published" | "unpublished"
  targetLibraryId?: string
  snippet?: string; locatorLabel?: string
  actions: Readonly<{ preview: boolean; download: boolean; edit: boolean; submit: boolean; review: boolean; publish: boolean }>
}>
export type WorkspaceState = "ready" | "loading" | "error" | "offline" | "forbidden" | "unconfigured" | "unavailable"
export type MaterialWorkspaceProps = Readonly<{
  audience: "student" | "staff"; state: WorkspaceState; error?: string
  items: readonly MaterialItem[]; total: number; offset: number; pageSize: number
  query: string; libraryId: string; libraries: readonly { id: string; label: string }[]
  canUpload: boolean; canManageLibrary: boolean
  searchPlaceholder?: string; scopeNotice?: string
  filterControls?: ReactNode; onClear?: () => void
  hasFilters?: boolean
  onJobs?: (item: MaterialItem) => void
  onSearch: (query: string, libraryId: string) => void; onPage: (offset: number) => void; onRefresh: () => void
  onUpload: () => void; onManageLibrary: () => void
  onAction: (action: "preview" | "download" | "edit" | "submit" | "review" | "publish", item: MaterialItem) => void
}>
const extractionLabels = { queued: "排队解析", running: "正在解析", succeeded: "解析完成", failed: "解析失败", canceled: "解析已取消" }
const publicationLabels = { draft: "草稿", submitted: "待审核", approved: "审核通过，待发布", rejected: "审核未通过", published: "已发布", unpublished: "本范围尚未发布" }
const actionLabels = { preview: "定位预览", download: "下载原件", edit: "编辑草稿", submit: "提交审核", review: "审核资料", publish: "发布版本" }

export function MaterialWorkspace(props: MaterialWorkspaceProps) {
  const [input, setInput] = useState(props.query), [library, setLibrary] = useState(props.libraryId)
  useEffect(() => { setLibrary(props.libraryId) }, [props.libraryId])
  // Fail closed if a future adapter accidentally passes staff-only records to the student view.
  const unsafe = props.audience === "student" && props.items.some(item => item.publication !== "published")
  return <PageContainer title="资料中心" description={props.audience === "student" ? "查找当前有权阅读的已发布资料与来源。" : "在获准范围提交资料，按固定版本审核与发布。"}
    actions={<>{props.audience === "staff" && props.canManageLibrary && <Button variant="secondary" onClick={props.onManageLibrary}>管理资料库</Button>}{props.audience === "staff" && props.canUpload && <Button onClick={props.onUpload}>上传资料</Button>}<Button variant="secondary" pending={props.state === "loading"} onClick={props.onRefresh}>刷新资料</Button></>}>
    <Notice>{props.scopeNotice || "只检索当前授权范围。扫描件、未解析或解析失败的文件没有可搜索正文；原件及定位内容打开时仍需校验权限。"}</Notice>
    <Panel title={props.audience === "student" ? "可阅读资料" : "授权资料与版本"}>
      <SearchFilters value={input} onChange={setInput} label="搜索资料" placeholder={props.searchPlaceholder || "标题、文件名、知识点或已提取正文"} pending={props.state === "loading"}
        onSearch={() => props.onSearch(input.trim(), library)} onClear={() => { setInput(""); setLibrary(""); if (props.onClear) props.onClear(); else props.onSearch("", "") }}>
        <Field label="资料范围"><select value={library} onChange={event => setLibrary(event.target.value)}><option value="">全部有权范围</option>{props.libraries.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></Field>
        {props.filterControls}
      </SearchFilters>
      {unsafe ? <StatePanel kind="forbidden" title="资料范围需要重新确认" description="当前返回的资料不符合学生阅读范围，请重新读取。" retry={props.onRefresh} />
        : props.state !== "ready" ? <StatePanel kind={props.state} description={props.error} retry={["error", "offline"].includes(props.state) ? props.onRefresh : undefined} />
        : <>{props.items.length ? <RecordList items={props.items} itemKey={item => item.versionId + ":" + (item.targetLibraryId || "")} title={item => item.title}
          fields={[{ label: "原文件", value: item => item.originalName || "知识点文本" }, { label: "所属范围", value: item => item.libraryLabel },
            { label: "固定版本", value: item => `第 ${item.versionNo} 版` }, { label: "解析状态", value: item => extractionLabels[item.extraction] },
            { label: "发布状态", value: item => publicationLabels[item.publication] }, { label: "匹配与定位", value: item => item.snippet ? <><p className="lc-material-snippet">{item.snippet}</p><span>{item.locatorLabel || "无页段定位"}</span></> : "无匹配片段（未搜索或未提取）" }]}
          actions={item => <>{(Object.keys(actionLabels) as (keyof typeof actionLabels)[]).filter(action => item.actions[action] && (props.audience !== "student" || action === "preview" || action === "download")).map(action => <Button key={action} variant="secondary" onClick={() => props.onAction(action, item)}>{actionLabels[action]}</Button>)}{props.audience === "staff" && props.onJobs && <Button variant="secondary" onClick={() => props.onJobs?.(item)}>本人解析任务</Button>}</>} />
          : <StatePanel kind="empty" title={props.query || props.libraryId || props.hasFilters ? "没有匹配的资料" : "暂无可访问资料"} description="尝试调整关键词和资料范围，或联系教师确认发布与授权。" />}
          <Pagination total={props.total} offset={props.offset} pageSize={props.pageSize} onChange={props.onPage} /></>}
    </Panel>
  </PageContainer>
}

export type PreviewChunk = Readonly<{ id: string; locatorLabel: string; text: string; isMatch?: boolean }>
export function MaterialPreview({ title, versionLabel, state, chunks, error, canDownload, onDownload, onRetry, onClose, hasMore, loadingMore, onMore }: {
  title: string; versionLabel: string; state: WorkspaceState; chunks: readonly PreviewChunk[]; error?: string
  canDownload: boolean; onDownload: () => void; onRetry: () => void; onClose: () => void
  hasMore?: boolean; loadingMore?: boolean; onMore?: () => void
}) {
  return <Dialog title="资料定位预览" long onClose={onClose}><h3 className="lc-material-title">{title}</h3><p>{versionLabel}</p>
    <Notice>预览为提取文字及原始页段定位。查看版式、图表和公式请下载有权原件；不在此渲染 Office 或执行文件内容。</Notice>
    {state !== "ready" ? <StatePanel kind={state} description={error} retry={["error", "offline"].includes(state) ? onRetry : undefined} /> : chunks.length ? <ol className="lc-material-chunks">{chunks.map(chunk => <li key={chunk.id} className={chunk.isMatch ? "lc-material-match" : undefined}><h3>{chunk.locatorLabel}{chunk.isMatch && " · 命中页段"}</h3><p>{chunk.text}</p></li>)}</ol> : <StatePanel kind="empty" title="暂无可预览文字" description="扫描件或未成功解析的资料不提供正文定位。" />}
    <div className="lc-actions">{hasMore && onMore && <Button variant="secondary" pending={loadingMore} onClick={onMore}>读取后续页段</Button>}<Button variant="secondary" onClick={onClose}>关闭预览</Button>{canDownload && <Button onClick={onDownload}>下载有权原件</Button>}</div>
  </Dialog>
}

export type UploadProgress = Readonly<{ state: "idle" | "uploading" | "queued" | "running" | "failed" | "uncertain"; sentBytes: number; totalBytes: number; error?: string }>
export function MaterialUpload({ targets, progress, onSubmit, onCancel, onClose, children, initialTitle = "", initialLibraryId, targetControl, selectedLibraryId }: {
  targets: readonly { id: string; label: string }[]; progress: UploadProgress
  onSubmit: (input: { file: File; title: string; libraryId: string }) => void; onCancel: () => void; onClose: () => void
  children?: ReactNode
  initialTitle?: string; initialLibraryId?: string
  targetControl?: ReactNode; selectedLibraryId?: string
}) {
  const [title, setTitle] = useState(initialTitle), [library, setLibrary] = useState(initialLibraryId || targets[0]?.id || ""), [file, setFile] = useState<File>(), [error, setError] = useState("")
  const busy = ["uploading", "queued", "running"].includes(progress.state), uncertain = progress.state === "uncertain"
  const percent = progress.totalBytes > 0 ? Math.max(0, Math.min(100, Math.floor(100 * progress.sentBytes / progress.totalBytes))) : 0
  return <Dialog title="上传授权资料" long busy={busy || uncertain} onClose={onClose}>
    <Notice>可提交范围不等于整库管理权。上传后须等待解析、审核与发布；上传完成不表示学生已可阅读。</Notice>
    <form className="lc-form" onSubmit={event => { event.preventDefault(); setError(""); if (!file) { setError("请选择资料文件。"); return }
      if (!title.trim()) { setError("资料名称不能为空。"); return }
      const format = file.name.split(".").pop()?.toLowerCase()
      if (!format || !["pdf", "pptx", "docx", "txt"].includes(format)) { setError("仅接收 PDF、PPTX、DOCX 和 TXT。"); return }
      if (!file.size || file.size > (format === "txt" ? 1048576 : 20971520)) { setError(format === "txt" ? "TXT 须非空且不超过 1 MiB。" : "文件须非空且不超过 20 MiB。"); return }
      onSubmit({ file, title: title.trim(), libraryId: selectedLibraryId ?? library })
    }}>
      <Field label="资料名称"><input value={title} onChange={event => setTitle(event.target.value)} required maxLength={200} disabled={busy || uncertain} /></Field>
      {targetControl || <Field label="提交范围"><select value={library} onChange={event => setLibrary(event.target.value)} required disabled={busy || uncertain || !targets.length}>{!targets.length && <option value="">暂无可提交范围</option>}{targets.map(target => <option key={target.id} value={target.id}>{target.label}</option>)}</select></Field>}
      <Field label="资料文件" hint="PDF / PPTX / DOCX 最多 20 MiB，TXT 最多 1 MiB。扫描件暂不支持 OCR。"><input type="file" accept=".pdf,.pptx,.docx,.txt" disabled={busy || uncertain} onChange={event => setFile(event.target.files?.[0])} /></Field>
      {children}
      {(error || progress.error) && <Notice kind="error">{error || progress.error}</Notice>}
      {progress.state !== "idle" && <div className="lc-material-progress" role="status"><p>{({ uploading: "正在传输原件", queued: "原件已接收，排队解析", running: "正在解析资料", failed: "处理失败，请核对原因后重试", uncertain: "结果尚未确认，保留本次文件与参数重试" })[progress.state]}</p>
        {progress.state === "uploading" && <><progress aria-label="文件上传进度" value={percent} max={100} /><span>{percent}%（{progress.sentBytes} / {progress.totalBytes} 字节）</span></>}</div>}
      <div className="lc-actions"><Button variant="secondary" disabled={busy || uncertain} onClick={onClose}>关闭上传</Button>{(busy || uncertain) && <Button variant="secondary" onClick={onCancel}>取消本次处理</Button>}<Button type="submit" disabled={busy || !targets.length}>{uncertain ? "核对原请求并重试" : "上传并解析"}</Button></div>
    </form>
  </Dialog>
}

export function MaterialReview({ title, versionLabel, authorization, warnings, pending, error, onConfirm, onClose }: {
  title: string; versionLabel: string; authorization: string; warnings: readonly string[]; pending: boolean; error?: string
  onConfirm: (decision: { decision: "approved" | "rejected"; reason: string; warningsAcknowledged: boolean; originalAuthorized: boolean }) => void; onClose: () => void
}) {
  const [decision, setDecision] = useState<"approved" | "rejected">("approved"), [reason, setReason] = useState("")
  const [acknowledged, setAcknowledged] = useState(false), [authorized, setAuthorized] = useState(false)
  return <Dialog title="审核资料版本" long busy={pending} onClose={onClose}><h3 className="lc-material-title">{title}</h3><p>{versionLabel}</p>
    <Notice kind="warning">决定绑定当前固定版本。审核通过后仍须单独发布；发布不能扩大原件的授权范围。</Notice>
    <Panel title="原件授权说明"><p className="lc-material-snippet">{authorization || "未提供授权说明，不能批准。"}</p></Panel>
    {warnings.length > 0 ? <Panel title="解析警告"><ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></Panel> : <p>当前无解析警告，仍须确认已核对本次解析结果。</p>}
    <form className="lc-form" onSubmit={event => { event.preventDefault(); onConfirm({ decision, reason: reason.trim(), warningsAcknowledged: acknowledged, originalAuthorized: authorized }) }}>
      <Field label="审核决定"><select value={decision} disabled={pending} onChange={event => setDecision(event.target.value as typeof decision)}><option value="approved">审核通过</option><option value="rejected">退回修改</option></select></Field>
      <Field label="处理说明"><textarea value={reason} onChange={event => setReason(event.target.value)} maxLength={1000} required={decision === "rejected"} disabled={pending} /></Field>
      {decision === "approved" && <><label className="lc-material-check"><input type="checkbox" checked={authorized} onChange={event => setAuthorized(event.target.checked)} disabled={pending} required />已核对整份原件在目标范围的阅读与下载授权</label>
        <label className="lc-material-check"><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} disabled={pending} required />已逐项核对当前解析警告</label></>}
      {error && <Notice kind="error">{error}</Notice>}
      <div className="lc-actions"><Button variant="secondary" disabled={pending} onClick={onClose}>取消审核</Button><Button type="submit" pending={pending} disabled={decision === "approved" && !authorization}>确认审核决定</Button></div>
    </form>
  </Dialog>
}

export function MaterialPublish({ title, versionLabel, targetLabel, pending, error, onConfirm, onClose }: {
  title: string; versionLabel: string; targetLabel: string; pending: boolean; error?: string; onConfirm: () => void; onClose: () => void
}) {
  return <Dialog title="发布已审核版本" busy={pending} onClose={onClose}><h3 className="lc-material-title">{title}</h3><p>{versionLabel}</p><p>发布范围：{targetLabel}</p>
    <Notice kind="warning">仅发布本次已审核的固定版本。发布前服务端将重新校验审核记录、当前权限和原件授权；不能因版本已审核而跳过这些检查。</Notice>
    {error && <Notice kind="error">{error}</Notice>}<div className="lc-actions"><Button variant="secondary" disabled={pending} onClick={onClose}>暂不发布</Button><Button pending={pending} onClick={onConfirm}>确认发布本版本</Button></div>
  </Dialog>
}
