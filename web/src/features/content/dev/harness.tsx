import { useState } from "react"
import { createRoot } from "react-dom/client"
import "../../../styles/index.css"
import { MaterialPreview, MaterialPublish, MaterialReview, MaterialUpload, MaterialWorkspace, type MaterialItem, type UploadProgress, type WorkspaceState } from "../ContentWorkspace"
import { Notice } from "../../../components/labconnect"

if (!import.meta.env.DEV) throw new Error("资料夹具仅限开发环境")
const actions = { preview: true, download: true, edit: false, submit: false, review: false, publish: false }
const fixture: readonly MaterialItem[] = [
  { versionId: "demo-published", title: "实验室通用安全：个人防护与应急处置", originalName: "合成_实验室个人防护与应急处置手册.pdf", libraryLabel: "通用安全示范班 · 已发布范围", versionNo: 2, extraction: "succeeded", publication: "published", snippet: "进入实验室前应核对个人防护要求。合成文字用于界面验证，不作为专业安全指导。", locatorLabel: "第 3 页 · 第 2 段", actions },
  { versionId: "demo-draft", title: "化学安全：" + "长文件名与跨学院课程资料".repeat(7), originalName: "合成_" + "化学实验室安全资料_".repeat(12) + ".pptx", libraryLabel: "本人可提交范围 · 不授予整库管理", versionNo: 1, extraction: "failed", publication: "draft", actions: { ...actions, preview: false, download: false, edit: true, submit: true } },
  { versionId: "demo-review", title: "待审核的合成资料版本", originalName: "合成审核资料.docx", libraryLabel: "有权审核的示范范围", versionNo: 3, extraction: "succeeded", publication: "submitted", actions: { ...actions, review: true } },
  { versionId: "demo-approved", title: "已审核待发布的合成资料", originalName: "合成发布资料.pdf", libraryLabel: "合成发布范围", versionNo: 4, extraction: "succeeded", publication: "approved", actions: { ...actions, publish: true } },
]
function Harness() {
  const [audience, setAudience] = useState<"staff" | "student">("staff"), [state, setState] = useState<WorkspaceState>("ready")
  const [query, setQuery] = useState(""), [library, setLibrary] = useState(""), [offset, setOffset] = useState(0)
  const [dialog, setDialog] = useState<"upload" | "preview" | "review" | "publish">(), [selected, setSelected] = useState<MaterialItem>(fixture[0])
  const [uploadScenario, setUploadScenario] = useState<UploadProgress["state"]>("uncertain")
  const [progress, setProgress] = useState<UploadProgress>({ state: "idle", sentBytes: 0, totalBytes: 0 }), [receipt, setReceipt] = useState("")
  const rows = fixture.filter(item => audience !== "student" || item.publication === "published").filter(item => !query || (item.title + item.originalName + item.snippet).includes(query))
  return <><aside className="lc-content-fixture"><strong>开发夹具 · 合成资料 · 非正式业务</strong><p>仅验证组件 props、排版和交互，不连接资料 API，不保存、上传或发布真实数据。</p>
    <div className="lc-content-fixture-controls"><label>夹具身份<select value={audience} onChange={event => { setAudience(event.target.value as typeof audience); setDialog(undefined); setReceipt(""); setQuery(""); setOffset(0) }}><option value="staff">教职人员</option><option value="student">学生</option></select></label>
      <label>夹具状态<select value={state} onChange={event => setState(event.target.value as WorkspaceState)}>{["ready", "loading", "error", "offline", "forbidden", "unconfigured", "unavailable"].map(value => <option key={value}>{value}</option>)}</select></label>
      <label>夹具上传状态<select value={uploadScenario} onChange={event => setUploadScenario(event.target.value as UploadProgress["state"])}>{["uncertain", "uploading", "queued", "running", "failed"].map(value => <option key={value}>{value}</option>)}</select></label></div></aside>
    <div className="lc-content-fixture-main">{receipt && <Notice>{receipt}</Notice>}
      <MaterialWorkspace key={audience} audience={audience} state={state} error="开发夹具状态，不代表服务端响应。" items={rows.slice(offset, offset + 2)} total={rows.length} offset={offset} pageSize={2} query={query} libraryId={library} libraries={[{ id: "fixture", label: "合成范围" }]} canUpload={audience === "staff"} canManageLibrary={false}
        onSearch={(text, id) => { setQuery(text); setLibrary(id); setOffset(0) }} onPage={setOffset} onRefresh={() => { setState("ready"); setReceipt("") }} onManageLibrary={() => setReceipt("开发夹具：未执行库管理。")}
        onUpload={() => { setProgress({ state: "idle", sentBytes: 0, totalBytes: 0 }); setDialog("upload") }} onAction={(action, item) => { setSelected(item); if (action === "preview" || action === "review" || action === "publish") setDialog(action); else setReceipt(`开发夹具：已触发 ${action} 回调，未执行正式业务。`) }} />
      {dialog === "preview" && <MaterialPreview title={selected.title} versionLabel={`第 ${selected.versionNo} 版 · 合成版本`} state="ready" chunks={[{ id: "fixture-chunk", locatorLabel: "第 3 页 · 第 2 段", text: "合成定位文字。\n<script>该文字必须作为纯文本显示，不执行脚本。</script>" }]} canDownload={selected.actions.download} onDownload={() => setReceipt("开发夹具：已触发下载回调，未下载原件。")} onRetry={() => {}} onClose={() => setDialog(undefined)} />}
      {dialog === "upload" && <MaterialUpload targets={[{ id: "fixture", label: "合成可提交范围" }]} progress={progress} onSubmit={input => setProgress({ state: uploadScenario, sentBytes: Math.floor(input.file.size / 2), totalBytes: input.file.size, error: uploadScenario === "uncertain" || uploadScenario === "failed" ? "开发夹具：未发送原件，用于核对结果不确定或失败时的交互。" : undefined })} onCancel={() => { setDialog(undefined); setReceipt("开发夹具：已触发取消回调，未取消服务端任务。") }} onClose={() => setDialog(undefined)} />}
      {dialog === "review" && <MaterialReview title={selected.title} versionLabel="第3版 · 合成固定版本" authorization="合成授权说明：仅用于开发组件预览。" warnings={["部分图形没有对应可提取文本，请核原件。"]} pending={false} onConfirm={() => setReceipt("开发夹具：已触发审核回调，未审核或发布正式版本。")} onClose={() => setDialog(undefined)} />}
      {dialog === "publish" && <MaterialPublish title={selected.title} versionLabel="第4版 · 合成固定版本" targetLabel={selected.libraryLabel} pending={false} onConfirm={() => setReceipt("开发夹具：已触发发布回调，未发布正式版本。")} onClose={() => setDialog(undefined)} />}
    </div></>
}
createRoot(document.getElementById("root")!).render(<Harness />)
