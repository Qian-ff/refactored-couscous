import { expect, test, type APIRequestContext, type Page } from "@playwright/test"
import { randomUUID, createHash } from "node:crypto"
import fs from "node:fs/promises"
import path from "node:path"
import { demoAccounts, reportDirectory } from "../../../others/scripts/web-environment.mjs"

// Run only after A publishes the main API runtime identity. Shared setup checks both sources.
test.use({ trace: "off", actionTimeout: 15_000 })
const api = process.env.LABCONNECT_API_URL || "http://127.0.0.1:8000"
const demo = demoAccounts()
async function call(request: APIRequestContext, token: string, method: string, route: string, body?: unknown, expected = 200) {
  const response = await request.fetch(api + "/api/v1" + route, { method, data: body, headers: { Authorization: "Bearer " + token, "Idempotency-Key": randomUUID() } })
  expect(response.status(), method + " " + route).toBe(expected)
  return response.json()
}
async function token(request: APIRequestContext, username: string, school = "demo-a") {
  return (await call(request, "", "POST", "/auth/login", { school_code: school, username, password: demo.password })).access_token as string
}
async function login(page: Page, username: string) {
  await page.addInitScript(value => localStorage.setItem("safelab.service", value), api)
  await page.goto("/#/content/materials")
  await page.getByLabel("学校代码", { exact: true }).fill("demo-a")
  await page.getByLabel("登录账号", { exact: true }).fill(username)
  await page.getByLabel("登录密码", { exact: true }).fill(demo.password)
  await page.getByRole("button", { name: "登录", exact: true }).click()
  await expect(page.getByRole("heading", { level: 1, name: "资料中心", exact: true })).toBeVisible()
}
async function capture(page: Page, name: string) {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
    await page.evaluate(() => document.fonts.ready)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
    await page.screenshot({ path: path.join(reportDirectory, name + "-" + width + ".png"), fullPage: true })
  }
  await page.setViewportSize({ width: 1440, height: 1000 })
}
test("真实资料：建库上传解析、审核发布、学生预览下载与基本权限", async ({ page, request, context }, info) => {
  test.setTimeout(180_000)
  const suffix = Date.now().toString(36) + randomUUID().slice(0, 4), courseTitle = "D1资料演示班" + suffix, libraryTitle = "D1授权资料库" + suffix, title = "D1实验室安全资料" + suffix
  const teacher = await token(request, "teacher"), student = await token(request, "student")
  const college = (await call(request, teacher, "GET", "/courses/context")).colleges[0].id
  const teacherId = (await call(request, teacher, "GET", "/auth/me")).id
  const course = await call(request, teacher, "POST", "/courses", { college_id: college, teacher_id: teacherId, code: "D1_" + suffix, title: courseTitle }, 201)
  const management = await call(request, teacher, "GET", "/courses/" + course.id + "/management")
  const invitation = await call(request, teacher, "POST", "/courses/" + course.id + "/invite", { revision: management.revision, expires_at: new Date(Date.now() + 3600_000).toISOString() })
  await call(request, student, "POST", "/enrollments/join", { invitation_code: invitation.code })
  const origins = new Set<string>()
  page.on("request", request => { if (request.url().includes("/api/v1/")) origins.add(new URL(request.url()).origin) })
  await login(page, "teacher")
  await page.getByRole("button", { name: "新建资料库", exact: true }).click()
  await page.getByLabel("查找归属范围", { exact: true }).fill(courseTitle)
  await page.getByRole("dialog").getByRole("button", { name: "搜索", exact: true }).click()
  await page.getByLabel("归属对象", { exact: true }).selectOption(course.id)
  await page.getByLabel("资料库名称", { exact: true }).fill(libraryTitle)
  await page.getByLabel("发布阅读对象", { exact: true }).selectOption("all")
  await page.getByRole("button", { name: "创建资料库", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  const libraries = await call(request, teacher, "GET", "/content/libraries?q=" + encodeURIComponent(libraryTitle))
  const library = libraries.items.find((row: { title: string }) => row.title === libraryTitle)
  expect(library).toBeTruthy()
  await page.getByRole("button", { name: "查找更多资料范围", exact: true }).click()
  await page.getByLabel("查找资料库", { exact: true }).fill(libraryTitle)
  await page.getByRole("dialog").getByRole("button", { name: "搜索", exact: true }).click()
  await page.getByRole("button", { name: "选择此资料范围", exact: true }).click()
  for (let attempt = 0; attempt < 3 && !await page.getByRole("button", { name: "上传资料", exact: true }).count(); attempt++) {
    const capabilities = page.waitForResponse(response => response.url() === api + "/api/v1/content/capabilities")
    await page.getByRole("button", { name: "刷新资料", exact: true }).click()
    const value = await (await capabilities).json()
    if (value.parser_available && value.storage_available) break
  }
  await expect(page.getByRole("button", { name: "上传资料", exact: true })).toBeVisible({ timeout: 10_000 })
  await page.getByRole("button", { name: "上传资料", exact: true }).click()
  await page.getByLabel("资料名称", { exact: true }).fill(title)
  await page.getByLabel("查找可提交范围", { exact: true }).fill(libraryTitle)
  await page.getByRole("button", { name: "查找提交范围", exact: true }).click()
  await page.getByLabel("提交范围", { exact: true }).selectOption(library.id)
  const bodyMarker = "正文定位关键词" + suffix
  const bytes = Buffer.from("合成资料：实验室防护与应急流程。\n仅用于研发功能验证，不作为专业安全指南。\n" + bodyMarker + "\n")
  await page.getByLabel("资料文件", { exact: true }).setInputFiles({ name: "合成安全资料_UTF8.txt", mimeType: "text/plain", buffer: bytes })
  await page.getByLabel("原作者", { exact: true }).fill("合成演示内容")
  await page.getByRole("button", { name: "上传并解析", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  let versionId = "", materialId = ""
  await expect.poll(async () => {
    const versions = await call(request, teacher, "GET", "/content/materials?library_id=" + library.id)
    const row = versions.items.find((item: { title: string }) => item.title === title)
    versionId = row?.version_id || ""; materialId = row?.material_id || ""
    return row?.extraction_state
  }, { timeout: 90_000, intervals: [1000, 2000] }).toBe("succeeded")
  await page.getByRole("button", { name: "刷新资料", exact: true }).click()
  const row = page.locator(".lc-records>li").filter({ has: page.getByRole("heading", { level: 3, name: title, exact: true }) })
  await expect(row).toContainText("解析完成")
  await row.getByRole("button", { name: "提交审核", exact: true }).click()
  await page.getByLabel("整份原件授权说明", { exact: true }).fill("合成文字由研发人员创建，授权本演示教学班阅读与下载整份原件。")
  await page.getByRole("button", { name: "提交审核申请", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await row.getByRole("button", { name: "审核资料", exact: true }).click()
  await page.getByLabel("已核对整份原件在目标范围的阅读与下载授权").check()
  if (await page.getByLabel("已逐项核对当前解析警告").count()) await page.getByLabel("已逐项核对当前解析警告").check()
  await page.getByRole("button", { name: "确认审核决定", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await row.getByRole("button", { name: "发布版本", exact: true }).click()
  await page.getByRole("button", { name: "确认发布本版本", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(row).toContainText("已发布")
  await capture(page, "content-real-teacher-published")
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  await login(page, "student")
  await page.getByLabel("搜索资料", { exact: true }).fill(bodyMarker)
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await expect(row).toContainText("已发布")
  await expect(page.getByRole("button", { name: "上传资料", exact: true })).toHaveCount(0)
  await expect(row.getByRole("button", { name: "编辑草稿", exact: true })).toHaveCount(0)
  await row.getByRole("button", { name: "定位预览", exact: true }).click()
  await expect(page.getByRole("dialog")).toContainText(bodyMarker)
  await expect(page.getByRole("dialog")).toContainText("第 3 段")
  await expect(page.getByRole("dialog")).toContainText("命中页段")
  const downloaded = page.waitForEvent("download")
  await page.getByRole("button", { name: "下载有权原件", exact: true }).click()
  const download = await downloaded, file = await download.path()
  expect(file).toBeTruthy()
  expect(createHash("sha256").update(await fs.readFile(file!)).digest("hex")).toBe(createHash("sha256").update(bytes).digest("hex"))
  await capture(page, "content-real-student-preview")
  await page.getByRole("button", { name: "关闭预览", exact: true }).click()
  await call(request, student, "PATCH", "/content/materials/" + materialId, { revision: 1, title: "不得修改" }, 403)
  const foreign = await token(request, "teacher_b", "demo-b")
  await call(request, foreign, "GET", "/content/versions/" + versionId, undefined, 403)
  await context.setOffline(true)
  await page.getByRole("button", { name: "刷新资料", exact: true }).click()
  await expect(page.getByRole("heading", { name: "网络已断开", exact: true })).toBeVisible()
  await context.setOffline(false)
  await page.getByRole("button", { name: "刷新资料", exact: true }).click()
  await expect(row).toContainText("已发布")
  expect([...origins]).toEqual([new URL(api).origin])
  await info.attach("actual-api-origins", { body: JSON.stringify([...origins]), contentType: "application/json" })
})

test("真实revision编辑和新固定版本不覆盖旧正文", async ({ page, request }) => {
  test.setTimeout(120_000)
  const suffix = Date.now().toString(36) + randomUUID().slice(0, 4), title = "D1版本验证" + suffix, libraryTitle = "D1版本资料库" + suffix
  const teacher = await token(request, "teacher"), teacherId = (await call(request, teacher, "GET", "/auth/me")).id
  const college = (await call(request, teacher, "GET", "/courses/context")).colleges[0].id
  const course = await call(request, teacher, "POST", "/courses", { college_id: college, teacher_id: teacherId, code: "D1V_" + suffix, title }, 201)
  const libraryId = (await call(request, teacher, "POST", "/content/libraries", { scope: "course", parent_id: course.id, title: libraryTitle, audience: "all" }, 201)).library_id
  const inputMarker = "知识点输入" + suffix
  const original = await call(request, teacher, "POST", "/content/materials/text", { library_id: libraryId, title, text: inputMarker + "。原始知识点，后续版本不得覆盖这段文字。" }, 201)
  const before = await call(request, teacher, "GET", "/content/versions/" + original.version_id)
  await login(page, "teacher")
  await page.getByLabel("搜索资料", { exact: true }).fill(inputMarker)
  await page.getByText("课程、类型与版本时间筛选", { exact: true }).click()
  await page.getByLabel("资料类型", { exact: true }).selectOption("text")
  await page.getByLabel("查找课程班级", { exact: true }).fill(title)
  await page.getByRole("button", { name: "查找课程候选", exact: true }).click()
  await page.getByLabel("课程班级筛选", { exact: true }).selectOption(course.id)
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  let row = page.locator(".lc-records>li").filter({ has: page.getByRole("heading", { name: title, level: 3, exact: true }) })
  await expect(row).toHaveCount(1)
  await page.getByLabel("版本创建截止时间（本机时间）", { exact: true }).fill("2000-01-01T00:00")
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await expect(page.getByRole("heading", { name: "没有匹配的资料", exact: true })).toBeVisible()
  await page.locator(".lc-search").getByRole("button", { name: "清空", exact: true }).click()
  await expect(page.getByLabel("课程班级筛选", { exact: true })).toHaveValue("")
  await expect(page.getByLabel("资料类型", { exact: true })).toHaveValue("")
  await page.getByLabel("搜索资料", { exact: true }).fill(inputMarker)
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await row.getByRole("button", { name: "编辑草稿", exact: true }).click()
  await page.getByLabel("名称", { exact: true }).fill(title + "更名")
  await page.getByRole("button", { name: "保存信息", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  const changed = await call(request, teacher, "GET", "/content/versions/" + original.version_id)
  expect(changed.material_revision).toBe(before.material_revision + 1)
  row = page.locator(".lc-records>li").filter({ has: page.getByRole("heading", { name: title + "更名", level: 3, exact: true }) })
  await row.getByRole("button", { name: "编辑草稿", exact: true }).click()
  await page.getByRole("button", { name: "上传新固定版本", exact: true }).click()
  await page.getByLabel("资料文件", { exact: true }).setInputFiles({ name: "新固定版本.txt", mimeType: "text/plain", buffer: Buffer.from("新版合成资料正文。") })
  await capture(page, "content-real-version-upload")
  await page.getByRole("button", { name: "上传并解析", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect.poll(async () => {
    const versions = await call(request, teacher, "GET", "/content/materials/" + original.material_id + "/versions")
    return versions.items.some((version: { version_no: number; extraction_state: string }) => version.version_no === 2 && version.extraction_state === "succeeded")
  }, { timeout: 90_000, intervals: [1000, 2000] }).toBeTruthy()
  const preserved = await call(request, teacher, "GET", "/content/versions/" + original.version_id)
  expect(preserved.content_hash).toBe(before.content_hash)
  const chunks = await call(request, teacher, "GET", "/content/versions/" + original.version_id + "/chunks")
  expect(chunks.items[0].text).toContain("原始知识点，后续版本不得覆盖这段文字。")
  await page.getByRole("button", { name: "查找资料库与管理权限", exact: true }).click()
  await page.getByLabel("查找资料库", { exact: true }).fill(libraryTitle)
  await page.getByRole("dialog").getByRole("button", { name: "搜索", exact: true }).click()
  const libraryRow = page.getByRole("dialog").locator("li").filter({ has: page.getByRole("heading", { name: libraryTitle, level: 3, exact: true }) })
  await libraryRow.getByRole("button", { name: "修改资料库", exact: true }).click()
  await page.getByLabel("名称", { exact: true }).fill(libraryTitle + "更名")
  await page.getByRole("button", { name: "保存信息", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  const libraries = await call(request, teacher, "GET", "/content/libraries?q=" + encodeURIComponent(libraryTitle))
  expect(libraries.items.find((library: { id: string }) => library.id === libraryId).title).toBe(libraryTitle + "更名")
})

test("真实分页：资料库、提交候选、资料及本人任务均可读后页", async ({ page, request }, info) => {
  test.setTimeout(240_000)
  const suffix = Date.now().toString(36) + randomUUID().slice(0, 4), scopePrefix = "D1分页库" + suffix, materialPrefix = "D1分页资料" + suffix
  const teacher = await token(request, "teacher"), teacherId = (await call(request, teacher, "GET", "/auth/me")).id
  const college = (await call(request, teacher, "GET", "/courses/context")).colleges[0].id
  const course = await call(request, teacher, "POST", "/courses", { college_id: college, teacher_id: teacherId, code: "D1P_" + suffix, title: scopePrefix }, 201)
  const libraries: string[] = []
  for (let i = 1; i <= 21; i++) libraries.push((await call(request, teacher, "POST", "/content/libraries", { scope: "course", parent_id: course.id, title: scopePrefix + "_" + String(i).padStart(2, "0"), audience: "all" }, 201)).library_id)
  // Minimal 20+1 normal records for real paging, parsed serially to avoid queue pressure.
  for (let i = 1; i <= 21; i++) {
    const created = await call(request, teacher, "POST", "/content/materials/text", { library_id: libraries[0], title: materialPrefix + "_" + i, text: "正常分页用合成短文字。" }, 201)
    await expect.poll(async () => (await call(request, teacher, "GET", "/content/versions/" + created.version_id)).extraction_state, { timeout: 45_000, intervals: [500, 1000] }).toBe("succeeded")
  }
  await login(page, "teacher")
  await page.getByRole("button", { name: "查找更多资料范围", exact: true }).click()
  await page.getByLabel("查找资料库", { exact: true }).fill(scopePrefix)
  await page.getByRole("dialog").getByRole("button", { name: "搜索", exact: true }).click()
  await expect(page.getByRole("dialog").locator(".lc-records>li")).toHaveCount(20)
  await page.getByRole("dialog").getByRole("button", { name: "下一页", exact: true }).click()
  await expect(page.getByRole("dialog").locator(".lc-records>li")).toHaveCount(1)
  await expect(page.getByRole("dialog")).toContainText(scopePrefix + "_21")
  await page.getByRole("dialog").getByRole("button", { name: "上一页", exact: true }).click()
  const first = page.getByRole("dialog").locator(".lc-records>li").filter({ has: page.getByRole("heading", { level: 3, name: scopePrefix + "_01", exact: true }) })
  await first.getByRole("button", { name: "选择此资料范围", exact: true }).click()
  await page.getByLabel("搜索资料", { exact: true }).fill(materialPrefix)
  await page.locator("main .lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await expect(page.locator("main .lc-records>li")).toHaveCount(20)
  await page.locator("main").getByRole("button", { name: "下一页", exact: true }).click()
  await expect(page.locator("main .lc-records>li")).toHaveCount(1)
  await page.getByRole("button", { name: "录入知识点文字", exact: true }).click()
  await page.getByLabel("查找可提交范围", { exact: true }).fill(scopePrefix)
  await page.getByRole("button", { name: "查找提交范围", exact: true }).click()
  const targetPage = page.waitForResponse(response => new URL(response.url()).pathname.endsWith("/content/submit-targets") && new URL(response.url()).searchParams.get("offset") === "20")
  await page.getByRole("button", { name: "下页提交范围", exact: true }).click()
  expect((await (await targetPage).json()).length).toBe(1)
  await page.getByLabel("提交范围", { exact: true }).selectOption(libraries[20])
  await page.getByRole("button", { name: "取消录入", exact: true }).click()
  const tasks = page.locator(".lc-content-product>.lc-panel")
  const taskPage = page.waitForResponse(response => new URL(response.url()).pathname.endsWith("/content/jobs") && new URL(response.url()).searchParams.get("offset") === "20")
  await tasks.getByRole("button", { name: "下一页", exact: true }).click()
  const result = await (await taskPage).json()
  expect(result.offset).toBe(20)
  expect(result.items.length).toBeGreaterThan(0)
  await expect(tasks.locator(".lc-records>li")).toHaveCount(result.items.length)
  await info.attach("paging-scope", { body: JSON.stringify({ libraries: "20+1", submitTargets: "20+1", materials: "20+1", jobsOffset: 20 }), contentType: "application/json" })
})

test("管理员资料库scope与停用恢复按实际revision保存", async ({ page, request }) => {
  const title = "D1校级范围" + Date.now().toString(36) + randomUUID().slice(0, 4)
  const admin = await token(request, "admin"), school = (await call(request, admin, "GET", "/auth/me")).school.id
  await login(page, "admin")
  await page.getByRole("button", { name: "新建资料库", exact: true }).click()
  await page.getByLabel("库范围", { exact: true }).selectOption("school")
  await page.getByLabel("归属对象", { exact: true }).selectOption(school)
  await page.getByLabel("资料库名称", { exact: true }).fill(title)
  await page.getByRole("button", { name: "创建资料库", exact: true }).click()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  for (const active of [false, true]) {
    const before = (await call(request, admin, "GET", "/content/libraries?include_inactive=true&q=" + encodeURIComponent(title))).items[0]
    await page.getByRole("button", { name: "查找资料库与管理权限", exact: true }).click()
    await page.getByLabel("查找资料库", { exact: true }).fill(title)
    await page.getByRole("dialog").getByRole("button", { name: "搜索", exact: true }).click()
    await page.getByRole("dialog").getByRole("button", { name: "修改资料库", exact: true }).click()
    await page.getByLabel("启用资料库", { exact: true }).setChecked(active)
    await page.getByRole("button", { name: "保存信息", exact: true }).click()
    await expect(page.getByRole("dialog")).toHaveCount(0)
    const after = (await call(request, admin, "GET", "/content/libraries?include_inactive=true&q=" + encodeURIComponent(title))).items[0]
    expect(after.scope).toBe("school")
    expect(after.active).toBe(active)
    expect(after.revision).toBe(before.revision + 1)
  }
})

test("本人任务可重新打开已完成的关联资料", async ({ page, request }) => {
  test.setTimeout(90_000)
  const suffix = Date.now().toString(36) + randomUUID().slice(0, 4), teacher = await token(request, "teacher"), title = "D1任务恢复" + suffix
  const teacherId = (await call(request, teacher, "GET", "/auth/me")).id
  const college = (await call(request, teacher, "GET", "/courses/context")).colleges[0].id
  const course = await call(request, teacher, "POST", "/courses", { college_id: college, teacher_id: teacherId, code: "D1J_" + suffix, title }, 201)
  const libraryId = (await call(request, teacher, "POST", "/content/libraries", { scope: "course", parent_id: course.id, title, audience: "staff" }, 201)).library_id
  const text = "合成任务关联正文" + suffix
  const material = await call(request, teacher, "POST", "/content/materials/text", { library_id: libraryId, title, text }, 201)
  await expect.poll(async () => (await call(request, teacher, "GET", "/content/versions/" + material.version_id)).extraction_state, { timeout: 45_000, intervals: [500, 1000] }).toBe("succeeded")
  await login(page, "teacher")
  await page.getByLabel("搜索资料", { exact: true }).fill(title)
  await page.locator("main .lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  const materialRow = page.locator("main .lc-records>li").filter({ has: page.getByRole("heading", { level: 3, name: title, exact: true }) })
  await materialRow.getByRole("button", { name: "本人解析任务", exact: true }).click()
  const tasks = page.locator(".lc-content-product>.lc-panel")
  await tasks.getByRole("button", { name: "查看任务资料", exact: true }).first().click()
  await expect(page.getByRole("dialog")).toContainText(title)
  await expect(page.getByRole("dialog")).toContainText(text)
})

for (const interruption of ["session", "unmount", "cancel"] as const) {
  test(`摘要等待取消保护：${interruption}之后不创建上传或发送字节`, async ({ page }) => {
    await login(page, "teacher")
    await expect(page.getByRole("button", { name: "上传资料", exact: true })).toBeVisible()
    // Delay only the tiny file digest. Spy on both generated methods, preventing accidental writes.
    await page.evaluate(async () => {
      const modulePath = "/src/client/index.ts"
      const { ContentService } = await import(modulePath)
      const counts = { createUpload: 0, uploadBytes: 0 }
      for (const method of ["createUpload", "uploadBytes"] as const) ContentService[method] = () => {
        counts[method]++
        return Promise.reject(new Error("Canceled preparation must not reach the SDK"))
      }
      const original = crypto.subtle.digest.bind(crypto.subtle)
      let release!: () => void
      const gate = new Promise<void>(resolve => { release = resolve })
      const guard = { counts, started: false, release }
      Object.assign(window, { uploadGuard: guard })
      crypto.subtle.digest = async (algorithm, bytes) => {
        const result = original(algorithm, bytes)
        guard.started = true
        await gate
        return result
      }
    })
    await page.getByRole("button", { name: "上传资料", exact: true }).click()
    await page.getByLabel("资料名称", { exact: true }).fill("D1取消文件准备")
    await page.getByLabel("资料文件", { exact: true }).setInputFiles({ name: "合成小文件.txt", mimeType: "text/plain", buffer: Buffer.from("仅用于摘要等待取消验证。") })
    await page.getByRole("button", { name: "上传并解析", exact: true }).click()
    await expect(page.locator(".lc-material-progress[role=status]")).toContainText("正在读取文件并校验完整性")
    await expect(page.getByRole("button", { name: "上传并解析", exact: true })).toBeDisabled()
    await expect.poll(() => page.evaluate(() => (window as unknown as { uploadGuard: { started: boolean } }).uploadGuard.started)).toBe(true)
    if (interruption === "session") {
      await page.evaluate(async () => {
        const modulePath = "/src/lib/api.ts"
        const session = await import(modulePath)
        const before = session.sessionSnapshot().generation
        await session.switchWorkRole("teacher") // Real session advance and server-confirmed identity.
        if (session.sessionSnapshot().generation === before) throw new Error("Session did not advance")
      })
    } else if (interruption === "unmount") {
      await page.evaluate(() => { location.hash = "/teaching/courses" })
    } else await page.getByRole("button", { name: "取消本次处理", exact: true }).click()
    await expect(page.getByRole("dialog")).toHaveCount(0)
    const counts = await page.evaluate(async () => {
      const guard = (window as unknown as { uploadGuard: { release: () => void; counts: { createUpload: number; uploadBytes: number } } }).uploadGuard
      guard.release()
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
      return guard.counts
    })
    expect(counts).toEqual({ createUpload: 0, uploadBytes: 0 })
  })
}
