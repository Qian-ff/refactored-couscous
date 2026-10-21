import { useEffect, useState } from "react"
import { Download, FileCheck2 } from "lucide-react"
import { ImportsService, type CsvInput, type CsvPreview } from "../../client"
import type { SessionSnapshot } from "../../lib/api"
import { ActionFeedback, commandHeaders, Field, Notice, useBusinessAction } from "./ui"

export function CsvImporter({ session, kind, schoolId, courseId, imported }: {
  session: SessionSnapshot; kind: "accounts" | "roster"; schoolId: string; courseId?: string; imported: () => void
}) {
  const [csv, setCsv] = useState("")
  const [checked, setChecked] = useState<{ source: string; preview: CsvPreview } | null>(null)
  const action = useBusinessAction(session)
  useEffect(() => { setCsv(""); setChecked(null); action.clear() }, [schoolId, courseId, kind])
  const body: CsvInput = { kind, school_id: schoolId, ...(courseId ? { course_id: courseId } : {}), csv }
  const current = checked?.source === csv ? checked.preview : null
  function download() {
    void action.run(async () => (await ImportsService.template({ query: { kind } })).data, result => {
      const url = URL.createObjectURL(new Blob([result.csv], { type: "text/csv;charset=utf-8" }))
      const link = document.createElement("a"); link.href = url; link.download = `labconnect-${kind}-template.csv`; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    }, "模板已准备下载，请按 UTF-8 CSV 格式填写")
  }
  return <div>
    <p>先预检全部数据，再确认整批提交。账号导入不会覆盖已有密码或授权，名单可以引用已开通学生。</p>
    <ActionFeedback action={action} />
    <div className="b1-actions"><button className="b1-button b1-secondary" type="button" disabled={action.pending} onClick={download}><Download size={17} />下载 CSV 模板</button></div>
    <Field label="选择 UTF-8 CSV 文件"><input type="file" accept=".csv,text/csv" disabled={action.pending} onChange={event => {
      const file = event.target.files?.[0]
      event.currentTarget.value = ""
      if (file) void action.run(async () => {
        if (file.size > 1_048_576) throw new Error("文件不得超过 1 MiB")
        return file.text()
      }, value => { setCsv(value); setChecked(null) }, "文件已读取，请先预检")
    }} /></Field>
    <Field label="CSV 内容" hint="每批最多 500 行；账号模板中为每个账号填写临时密码。内容仅保留在当前页面内存。">
      <textarea value={csv} disabled={action.pending} onChange={event => { setCsv(event.target.value); setChecked(null) }} spellCheck={false} />
    </Field>
    {!schoolId && <Notice>请先选择学校。</Notice>}
    <div className="b1-actions">
      <button type="button" className="b1-button b1-secondary" disabled={action.pending || !schoolId || !csv} onClick={() => {
        void action.run(async () => (await ImportsService.previewImport({ body })).data,
          preview => setChecked({ source: csv, preview }), "预检已完成")
      }}><FileCheck2 size={17} />预检文件</button>
      <button type="button" className="b1-button" disabled={action.pending || !current?.valid} onClick={() => {
        if (!current?.valid) return
        const payload = { ...body, preview_digest: current.digest }
        void action.run(async key => (await ImportsService.commitImport({ body: payload, headers: commandHeaders(key) })).data,
          () => { setCsv(""); setChecked(null); imported(); }, "整批提交成功", JSON.stringify(["csv-commit", payload]))
      }}>{action.pending ? "正在处理…" : `确认整批提交${current?.valid ? `（${current.row_count} 行）` : ""}`}</button>
    </div>
    {current && <Notice kind={current.valid ? "success" : "error"}>{current.valid ? `${current.row_count} 行全部通过预检，可以确认提交。` : `发现 ${current.errors.length} 个问题，请修正后重新预检；尚未写入。`}</Notice>}
    {current && current.errors.length > 0 && <div className="b1-table-wrap"><table className="b1-table"><thead><tr><th>行号</th><th>字段</th><th>问题</th></tr></thead><tbody>{current.errors.map((error, index) => <tr key={index}><td>{String(error.line ?? "—")}</td><td>{String(error.field ?? "—")}</td><td>{String(error.message ?? "格式不正确")}</td></tr>)}</tbody></table></div>}
    <p className="b1-inline-note">提交后若网络中断，先重试确认；同一内容会复用本次请求。修改文件或切换学校后需重新预检。</p>
  </div>
}
