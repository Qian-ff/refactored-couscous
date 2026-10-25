import { test, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"
import { root } from "../../../others/scripts/web-environment.mjs"

test("真实生成SDK保留原始上传下载字节，并复用会话取消和二进制错误反馈", async ({ page }) => {
  const runtime = JSON.parse(fs.readFileSync(path.join(root, "others/runtime/c02-public/api-runtime.json"), "utf8"))
  await page.goto("/")
  const result = await page.evaluate(async ({ password }) => {
    const apiPath = "/src/lib/api.ts"
    const clientPath = "/src/client/index.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    const { AuthService, ContentService } = await import(/* @vite-ignore */ clientPath)
    api.configureService("http://127.0.0.1:8002")
    let lastToken = ""
    const login = async (username: string) => {
      const response = await AuthService.login({ body: { school_code: "demo-a", username, password } })
      lastToken = response.data.access_token
      api.setToken(lastToken)
      return api.confirmSession()
    }
    const key = () => ({ "Idempotency-Key": crypto.randomUUID() })
    try {
      const admin = await login("admin")
      const library = await ContentService.createLibrary({ headers: key(), body: {
        title: "SDK binary " + crypto.randomUUID().slice(0, 8), scope: "school", parent_id: admin.school.id, audience: "all",
      } })
      await api.logoutSession()
      await login("teacher")
      const source = new TextEncoder().encode("实验安全与设备用电\n原始字节不能按JSON转义。")
      const digest = (bytes: ArrayBuffer) => crypto.subtle.digest("SHA-256", bytes).then(value =>
        [...new Uint8Array(value)].map(byte => byte.toString(16).padStart(2, "0")).join(""))
      const hash = await digest(source.buffer)
      const created = await ContentService.createUpload({ headers: key(), body: {
        library_id: library.data.library_id, title: "SDK binary original", original_name: "字节校验.txt", format: "txt",
        expected_bytes: source.length, expected_hash: hash,
      } })
      const sealed = await ContentService.uploadBytes({ path: { upload_id: created.data.upload_id },
        body: new Blob([source], { type: "application/octet-stream" }) })
      const versionId = sealed.data.version_id
      const downloaded = await ContentService.downloadVersion({ path: { version_id: versionId } })
      const blob = downloaded.data
      const bytes = await blob.arrayBuffer()
      const originalHash = await digest(bytes)
      const length = Number(downloaded.headers["content-length"])
      const disposition = String(downloaded.headers["content-disposition"])
      const pending = ContentService.downloadVersion({ path: { version_id: versionId } }).then(
        () => false, (error: unknown) => api.isStaleRequest(error))
      await api.logoutSession()
      const canceled = await pending
      await login("student")
      let deniedMessage = ""
      try { await ContentService.downloadVersion({ path: { version_id: versionId } }) }
      catch (error) { deniedMessage = api.message(error) }
      return { blob: blob instanceof Blob, sameHash: originalHash === hash, bytes: bytes.byteLength,
        expectedBytes: source.length, length, disposition, canceled, deniedMessage,
        credentialsPersisted: JSON.stringify(localStorage).includes(password) || JSON.stringify(localStorage).includes(lastToken) }
    } catch (error) {
      // Do not print Axios request configuration, tokens or login payloads on a failed test.
      throw new Error(api.message(error))
    } finally { await api.logoutSession().catch(() => {}) }
  }, { password: runtime.synthetic_password })
  expect(result.blob).toBe(true)
  expect(result.sameHash).toBe(true)
  expect(result.bytes).toBe(result.expectedBytes)
  expect(result.length).toBe(result.expectedBytes)
  expect(result.disposition).toContain("filename*=UTF-8''")
  expect(result.canceled).toBe(true)
  expect(result.deniedMessage).toContain("无权")
  expect(result.credentialsPersisted).toBe(false)
})
