import { expect, test } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"
import { reportDirectory } from "../../../others/scripts/web-environment.mjs"

test.use({ trace: "off" })
test("C1实际SDK原始字节上传和鉴权Blob下载", async ({ page }) => {
  test.setTimeout(90000)
  const root = path.resolve(import.meta.dirname, "../../..")
  const config = JSON.parse(fs.readFileSync(path.join(root, "others/runtime/c1-public/api-runtime.json"), "utf8"))
  const previous = JSON.parse(fs.readFileSync(path.join(root, "others/reports/c1-public/t2/live-http.json"), "utf8"))
  await page.goto("/")
  const result = await page.evaluate(async input => {
    const sdkPath = "/src/client/index.ts", sessionPath = "/src/lib/api.ts"
    const { AuthService, ContentQuestionsService } = await import(sdkPath)
    const session = await import(sessionPath)
    session.configureService("http://127.0.0.1:8002")
    const login = await AuthService.login({ body: { school_code: "demo-a", username: "teacher", password: input.password } })
    session.setToken(login.data.access_token)
    await session.confirmSession()
    const headers = () => ({ "Idempotency-Key": "t2-sdk-" + crypto.randomUUID() })
    const version = (await ContentQuestionsService.questionsVersion({ path: { version_id: input.version } })).data
    const exported = (await ContentQuestionsService.questionsCreateExport({ headers: headers(), body: {
      library_id: version.library_id, format: "csv", version_ids: [input.version], authorization_statement: "Synthetic SDK export" } })).data
    async function wait(taskId: string) {
      for (let attempt = 0; attempt < 160; attempt++) {
        const task = (await ContentQuestionsService.questionsTask({ path: { task_id: taskId } })).data
        if (task.state === "succeeded") return task
        if (["failed", "expired"].includes(task.state)) throw new Error(task.error_code || "Transfer failed")
        await new Promise(resolve => setTimeout(resolve, 200))
      }
      throw new Error("Candidate transfer timeout")
    }
    await wait(exported.task_id)
    const downloaded = (await ContentQuestionsService.questionsDownloadExport({ path: { task_id: exported.task_id } })).data
    if (!(downloaded instanceof Blob)) throw new Error("SDK download must return a Blob")
    const original = await downloaded.text()
    const changed = original.replace(version.payload.stem, "T2SDK合成" + crypto.randomUUID())
    if (changed === original) throw new Error("Synthetic CSV stem was not replaced")
    const bytes = new TextEncoder().encode(changed)
    const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(byte => byte.toString(16).padStart(2, "0")).join("")
    const created = (await ContentQuestionsService.questionsCreateImport({ headers: headers(), body: {
      library_id: version.library_id, format: "csv", expected_bytes: bytes.length, input_hash: hash } })).data
    let progress = false
    await ContentQuestionsService.questionsUploadInput({ path: { task_id: created.task_id }, headers: headers(),
      body: new Blob([bytes], { type: "application/octet-stream" }), onUploadProgress: () => { progress = true } })
    await wait(created.task_id)
    const preview = (await ContentQuestionsService.questionsImportStatus({ path: { batch_id: created.batch_id } })).data
    let repeated = 0
    try { await ContentQuestionsService.questionsUploadInput({ path: { task_id: created.task_id }, headers: headers(), body: new Blob([bytes]) }) }
    catch (error) { repeated = (error as { response?: { status: number } }).response?.status || 0 }
    return { blob: true, download_bytes: downloaded.size, uploaded_bytes: bytes.length, upload_hash: hash,
      preview_hash_matches: preview.input_hash === hash, preview_state: preview.state, progress, repeated_status: repeated }
  }, { password: config.synthetic_password, version: previous.formats[0].version })
  expect(result.preview_state).toBe("ready")
  expect(result.preview_hash_matches).toBe(true)
  expect(result.repeated_status).toBe(409)
  expect(result.download_bytes).toBeGreaterThan(0)
  fs.writeFileSync(path.join(reportDirectory, "sdk-transfer.json"), JSON.stringify(result, null, 2))
})
