import { useCallback, useEffect, useRef, useState } from "react"
import { ContentService, type Capabilities, type LibraryView, type SourceMetadata, type VersionView } from "../../client"
import { Button, Dialog, Field, Notice } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import { MaterialPreview, MaterialUpload, type UploadProgress } from "./ContentWorkspace"
import { locatorLabel } from "./material-adapter"
import { SourceFields } from "./SourceFields"
import { SubmitTargetChooser } from "./ScopeSelectors"
import { sessionSnapshot, subscribeSession } from "../../lib/api"

type Done = { onClose: () => void; onDone: (message: string, version?: { id: string; title: string }) => void }
type Target = { id: string; label: string }
export function ContentPreview({ version, onClose, onDownload }: { version: VersionView; onClose: () => void; onDownload: () => void }) {
  const match = version.search_match
  const [after, setAfter] = useState(match?.kind === "chunk" && match.chunk_id && match.ordinal != null ? Math.max(0, match.ordinal - 1) : 0)
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await ContentService.versionChunks({ path: { version_id: version.version_id }, query: { library_id: version.binding?.target_library_id || version.library_id, after, limit: 30 }, signal })).data, [version.version_id, version.library_id, version.binding?.target_library_id, after]))
  return <MaterialPreview title={version.title} versionLabel={`第 ${version.version_no} 版 · 按原文顺序分页读取`} state={resource.loading ? "loading" : resource.error ? resource.status === 403 ? "forbidden" : "error" : "ready"}
    chunks={(resource.data?.items || []).map(chunk => ({ id: chunk.id, text: chunk.text, locatorLabel: locatorLabel(chunk.locator), isMatch: match?.kind === "chunk" && match.chunk_id === chunk.id }))} error={resource.error} canDownload={!!version.actions?.download} onDownload={onDownload} onClose={onClose} onRetry={resource.reload}
    hasMore={resource.data?.next_ordinal != null} onMore={() => { if (resource.data?.next_ordinal != null) setAfter(resource.data.next_ordinal) }} />
}

export function ContentUpload({ targets, capabilities, version, onClose, onDone }: Done & { targets: readonly Target[]; capabilities?: Capabilities; version?: VersionView }) {
  const [target, setTarget] = useState(targets[0]?.id || ""), [targetLabel, setTargetLabel] = useState(targets[0]?.label || "")
  const [source, setSource] = useState<SourceMetadata>(version?.source_metadata || { origin: "upload" }), [encoding, setEncoding] = useState<"utf-8" | "gb18030">("utf-8"), [progress, setProgress] = useState<UploadProgress>({ state: "idle", sentBytes: 0, totalBytes: 0 })
  const uploadId = useRef<string | undefined>(undefined), attempt = useRef<{ generation: number; controller: AbortController; requested: boolean } | undefined>(undefined), alive = useRef(true), command = useCommand(), cancel = useCommand()
  useEffect(() => {
    alive.current = true
    const unsubscribe = subscribeSession(session => { if (attempt.current && session.generation !== attempt.current.generation) attempt.current.controller.abort() })
    return () => { alive.current = false; attempt.current?.controller.abort(); unsubscribe() }
  }, [])
  async function submit(input: { file: File; title: string; libraryId: string }) {
    if (!alive.current || (attempt.current && !attempt.current.controller.signal.aborted)) return
    const current = { generation: sessionSnapshot().generation, controller: new AbortController(), requested: false }
    attempt.current = current
    const valid = () => alive.current && attempt.current === current && !current.controller.signal.aborted && current.generation === sessionSnapshot().generation
    const format = input.file.name.split(".").pop()?.toLowerCase() as "pdf" | "pptx" | "docx" | "txt"
    const max = format === "txt" ? capabilities?.max_text_bytes || 1048576 : capabilities?.max_file_bytes || 20971520
    if (input.file.size > max || !(capabilities?.formats || ["pdf", "pptx", "docx", "txt"]).includes(format)) { current.controller.abort(); setProgress({ ...progress, state: "failed", error: "文件不符合当前服务支持的格式或大小。" }); return }
    setProgress({ state: "preparing", sentBytes: 0, totalBytes: input.file.size })
    let hash: string
    try {
      const bytes = await input.file.arrayBuffer()
      if (!valid()) return
      hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(byte => byte.toString(16).padStart(2, "0")).join("")
    } catch { if (valid()) { current.controller.abort(); setProgress({ state: "failed", sentBytes: 0, totalBytes: input.file.size, error: "无法读取文件并计算摘要，请重新选择可读取的文件。" }) }; return }
    if (!valid()) return
    const body = { library_id: input.libraryId, material_id: version?.material_id, title: input.title, original_name: input.file.name, format, encoding, expected_bytes: input.file.size, expected_hash: hash, source_metadata: source }
    const result = await command.run(JSON.stringify(body), async key => {
      if (!valid()) throw new DOMException("上传已取消", "AbortError")
      current.requested = true
      const created = await ContentService.createUpload({ body, signal: current.controller.signal, headers: { "Idempotency-Key": key } })
      if (!valid()) throw new DOMException("上传已取消", "AbortError")
      if (!created.data.upload_id) throw new Error("服务端未返回上传标识，请重新读取状态")
      uploadId.current = created.data.upload_id
      setProgress({ state: "uploading", sentBytes: 0, totalBytes: input.file.size })
      return ContentService.uploadBytes({ path: { upload_id: uploadId.current }, body: input.file, signal: current.controller.signal,
        onUploadProgress: event => { if (valid()) setProgress({ state: "uploading", sentBytes: event.loaded, totalBytes: input.file.size }) } })
    })
    if (!valid()) return
    current.controller.abort()
    if (result) onDone("原件已由服务端接收，解析任务已建立；请读取任务状态，尚未审核或发布。", result.data.version_id ? { id: result.data.version_id, title: input.title } : undefined)
    else setProgress(previous => ({ ...previous, state: "uncertain", error: "本次结果尚未确认。保留原文件和参数重试，或确认取消。" }))
  }
  const locked = ["preparing", "uploading", "uncertain"].includes(progress.state)
  return <MaterialUpload initialTitle={version?.title} initialLibraryId={version?.library_id} selectedLibraryId={version?.library_id || target} targetControl={version ? undefined : <SubmitTargetChooser value={target} label={targetLabel} onChange={(id, label) => { setTarget(id); setTargetLabel(label) }} disabled={locked} />} targets={version ? [{ id: version.library_id, label: "原资料所属库 · 新固定版本" }] : targets} progress={{ ...progress, error: cancel.error || command.error || progress.error }} onClose={onClose} onSubmit={input => { void submit(input) }} onCancel={async () => {
    const current = attempt.current
    current?.controller.abort()
    if (!alive.current || (current && current.generation !== sessionSnapshot().generation)) return
    if (current && !current.requested) { onDone("已取消本次文件准备，未发起上传。"); return }
    if (!uploadId.current) { setProgress(previous => ({ ...previous, state: "uncertain", error: "上传标识尚未确认。请保留原参数重试，再核对取消结果。" })); return }
    const result = await cancel.run("cancel-upload:" + uploadId.current, key => ContentService.cancelUpload({ path: { upload_id: uploadId.current! }, headers: { "Idempotency-Key": key } }))
    if (result) onDone("服务端已确认取消本次上传。")
  }}><Field label="TXT文字编码" hint="PDF、PPTX、DOCX不使用此选项。"><select value={encoding} onChange={e => setEncoding(e.target.value as typeof encoding)} disabled={locked}><option value="utf-8">UTF-8</option><option value="gb18030">GB18030</option></select></Field><SourceFields value={source} onChange={setSource} disabled={locked} /></MaterialUpload>
}

export function ContentEdit({ version, library, onClose, onDone, onNewVersion }: Done & { version?: VersionView; library?: LibraryView; onNewVersion?: (version: VersionView) => void }) {
  const [title, setTitle] = useState(version?.title || library?.title || ""), [active, setActive] = useState(library?.active ?? true), action = useCommand()
  return <Dialog title={library ? "修改资料库" : "修改资料名称"} busy={action.pending} onClose={onClose}>
    <p>按当前读取的信息保存；若资料已被修改，请关闭窗口、刷新后重新核对，避免覆盖他人的修改。</p>
    {version?.actions?.create_version && onNewVersion && <><Notice>已存在版本的原文不能覆盖。替换原件会建立新固定版本，并重新解析、审核和发布。</Notice><Button variant="secondary" pending={action.pending} onClick={async () => {
      const result = await action.run("new-version:" + version.version_id, async () => {
        const response = await ContentService.versionDetail({ path: { version_id: version.version_id } })
        if (!response.data.actions?.create_version) throw new Error("当前已无权创建新版本，请关闭窗口重新读取。")
        return response
      })
      if (result) onNewVersion(result.data)
    }}>上传新固定版本</Button></>}
    <form className="lc-form" onSubmit={async event => { event.preventDefault(); if (!title.trim()) return
      const result = await action.run("edit:" + (library?.id || version?.material_id) + ":" + JSON.stringify({ title: title.trim(), active, revision: library?.revision ?? version?.material_revision }), key => library
        ? ContentService.changeLibrary({ path: { library_id: library.id }, body: { revision: library.revision, title: title.trim(), active }, headers: { "Idempotency-Key": key } })
        : ContentService.changeMaterial({ path: { material_id: version!.material_id }, body: { revision: version!.material_revision!, title: title.trim() }, headers: { "Idempotency-Key": key } }))
      if (result) onDone("服务端已确认保存资料信息。")
    }}><Field label="名称"><input value={title} required maxLength={200} onChange={e => setTitle(e.target.value)} disabled={action.pending} /></Field>
      {library && <><label className="lc-material-check"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} disabled={action.pending} />启用资料库</label>{!active && <Notice kind="warning">保存后停用该资料库，后续访问和提交按服务端规则限制；已有固定版本与记录保留。</Notice>}</>}
      {action.error && <Notice kind="error">{action.error}</Notice>}<div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={onClose}>取消修改</Button><Button type="submit" pending={action.pending}>保存信息</Button></div>
    </form>
  </Dialog>
}
export function ContentSubmit({ version, targetLabel, onClose, onDone }: Done & { version: VersionView; targetLabel: string }) {
  const [statement, setStatement] = useState(""), [targetId, setTargetId] = useState(version.binding?.target_library_id || version.library_id), action = useCommand()
  const [selectedLabel, setSelectedLabel] = useState(targetLabel)
  return <Dialog title="提交当前版本审核" busy={action.pending} onClose={onClose}><p>{version.title} · 第 {version.version_no} 版</p><p>目标范围：{targetLabel}</p>
    <Notice>审核和发布仅绑定当前版本与这个目标。向其他范围共享须选择获准范围，并重新审核整份原件授权。</Notice>
    <form className="lc-form" onSubmit={async e => { e.preventDefault(); if (!statement.trim()) return
      const body = { version_id: version.version_id, target_library_id: targetId, authorization_statement: statement.trim() }
      const result = await action.run(JSON.stringify(body), key => ContentService.submitReview({ body, headers: { "Idempotency-Key": key } }))
      if (result) onDone("服务端已接收该版本的审核申请，尚未发布。")
    }}><SubmitTargetChooser fieldLabel="提审目标范围" value={targetId} label={selectedLabel} onChange={(id, label) => { setTargetId(id); setSelectedLabel(label) }} disabled={action.pending} />
      <Field label="整份原件授权说明"><textarea value={statement} onChange={e => setStatement(e.target.value)} required maxLength={2000} disabled={action.pending} /></Field>
      {action.error && <Notice kind="error">{action.error}</Notice>}<div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={onClose}>取消提审</Button><Button type="submit" pending={action.pending}>提交审核申请</Button></div></form>
  </Dialog>
}
export function TextMaterial({ targets, onClose, onDone }: Done & { targets: readonly Target[] }) {
  const [title, setTitle] = useState(""), [text, setText] = useState(""), [target, setTarget] = useState(targets[0]?.id || ""), [source, setSource] = useState<SourceMetadata>({ origin: "upload" }), action = useCommand()
  const [targetLabel, setTargetLabel] = useState(targets[0]?.label || "")
  return <Dialog title="录入授权知识点" long busy={action.pending} onClose={onClose}><form className="lc-form" onSubmit={async e => { e.preventDefault(); if (!title.trim() || !text.trim()) return
    const body = { title: title.trim(), text, library_id: target, source_metadata: source }
    const result = await action.run(JSON.stringify(body), key => ContentService.createText({ body, headers: { "Idempotency-Key": key } }))
    if (result) onDone("服务端已保存知识点固定版本；尚未审核或发布。", result.data.version_id ? { id: result.data.version_id, title: title.trim() } : undefined)
  }}><Field label="知识点名称"><input value={title} onChange={e => setTitle(e.target.value)} required maxLength={200} disabled={action.pending} /></Field>
    <Field label="知识点内容" hint="最多1 MiB UTF-8文字。"><textarea value={text} onChange={e => setText(e.target.value)} required maxLength={1048576} disabled={action.pending} /></Field>
    <SubmitTargetChooser value={target} label={targetLabel} onChange={(id, label) => { setTarget(id); setTargetLabel(label) }} disabled={action.pending} />
    <SourceFields value={source} onChange={setSource} disabled={action.pending} />{action.error && <Notice kind="error">{action.error}</Notice>}
    <div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={onClose}>取消录入</Button><Button type="submit" pending={action.pending}>保存知识点</Button></div></form></Dialog>
}
