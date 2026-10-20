import { test, expect } from "@playwright/test"
import { createServer } from "node:http"
import { requireService, sourceIdentity } from "../../../others/scripts/web-environment.mjs"

test("相同页面标题或错误源码 SHA 不能成为测试证据", async () => {
  const expected = sourceIdentity("web")
  let altered = "source_sha"
  const server = createServer((_request, response) => {
    response.setHeader("Content-Type", "application/json")
    response.end(JSON.stringify({ ...expected, [altered]: "another-checkout" }))
  })
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve))
  try {
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("Expected a test TCP port")
    for (const key of ["source_sha", "worktree_id", "source_fingerprint", "contract"]) {
      altered = key
      await expect(requireService(`http://127.0.0.1:${address.port}`, expected)).rejects.toThrow("another or stale checkout")
    }
  } finally { await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve())) }
})

test("身份切换经服务端确认并取消旧请求，过期 401 不清除新身份", async ({ page }) => {
  let release: (() => void) | undefined
  let oldStarted: (() => void) | undefined
  const started = new Promise<void>(resolve => { oldStarted = resolve })
  await page.route("**/api/v1/auth/me", async route => {
    const role = route.request().headers()["x-work-role"] || "teacher"
    await route.fulfill({ json: { id: "synthetic", display_name: "合成测试", grants: [], effective_grants: [],
      available_work_roles: ["teacher", "administrator"], active_work_role: role } })
  })
  await page.route("**/api/v1/courses", async route => {
    oldStarted?.()
    await new Promise<void>(resolve => { release = resolve })
    await route.fulfill({ status: 401, json: { detail: "old session expired" } }).catch(() => {})
  })
  await page.goto("/")
  await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const sdkPath = "/src/client/index.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    const sdk = await import(/* @vite-ignore */ sdkPath)
    api.setToken("synthetic-test-token")
    await api.confirmSession()
    ;(window as any).oldRequest = sdk.CoursesService.courses().then(() => "accepted", (error: unknown) => api.isStaleRequest(error) ? "canceled" : "error")
  })
  await started
  const switched = await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    await api.switchWorkRole("administrator")
    return { state: api.sessionSnapshot(), old: await (window as any).oldRequest }
  })
  release?.()
  expect(switched.state.workRole).toBe("administrator")
  expect(switched.state.phase).toBe("ready")
  expect(switched.old).toBe("canceled")
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain("synthetic-test-token")
})

test("撤销所选身份、当前 401 与更换服务地址均清除会话", async ({ page }) => {
  await page.goto("/")
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 403, json: { detail: "身份已撤销" } }))
  expect(await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    api.setToken("synthetic-a")
    try { await api.switchWorkRole("administrator") } catch {}
    return api.sessionSnapshot().phase
  })).toBe("anonymous")
  await page.unroute("**/api/v1/auth/me")
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 401, json: { detail: "会话已撤销" } }))
  expect(await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    api.setToken("synthetic-b")
    try { await api.confirmSession() } catch {}
    return api.sessionSnapshot().reason
  })).toBe("unauthorized")
  expect(await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    api.setToken("synthetic-c")
    api.configureService("https://synthetic.example.invalid")
    return api.sessionSnapshot().phase
  })).toBe("anonymous")
})

test("退出请求失败也结束本地会话", async ({ page }) => {
  await page.route("**/api/v1/auth/logout", route => route.abort("failed"))
  await page.goto("/")
  const state = await page.evaluate(async () => {
    const apiPath = "/src/lib/api.ts"
    const api = await import(/* @vite-ignore */ apiPath)
    api.setToken("synthetic-token")
    try { await api.logoutSession() } catch {}
    return api.sessionSnapshot()
  })
  expect(state.phase).toBe("anonymous")
  expect(state.user).toBeUndefined()
})
