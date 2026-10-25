import { expect, test, type APIRequestContext, type Page } from "@playwright/test"
import { randomUUID, createHash } from "node:crypto"
import fs from "node:fs/promises"
import path from "node:path"
import { demoAccounts, reportDirectory } from "../../../others/scripts/web-environment.mjs"

// Run only after A publishes the main API runtime identity. Shared setup checks both sources.
test.use({ trace: "off" })
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
  const course = await call(request, teacher, "POST", "/courses", { college_id: college, code: "D1_" + suffix, title: courseTitle }, 201)
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
  await page.getByLabel("资料范围", { exact: true }).selectOption(library.id)
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await page.getByRole("button", { name: "上传资料", exact: true }).click()
  await page.getByLabel("资料名称", { exact: true }).fill(title)
  await page.getByLabel("提交范围", { exact: true }).selectOption(library.id)
  const bytes = Buffer.from("合成资料：实验室防护与应急流程。\n仅用于研发功能验证，不作为专业安全指南。\n")
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
  await page.getByLabel("搜索资料", { exact: true }).fill(title)
  await page.locator(".lc-search").getByRole("button", { name: "搜索", exact: true }).click()
  await expect(row).toContainText("已发布")
  await expect(page.getByRole("button", { name: "上传资料", exact: true })).toHaveCount(0)
  await expect(row.getByRole("button", { name: "编辑草稿", exact: true })).toHaveCount(0)
  await row.getByRole("button", { name: "定位预览", exact: true }).click()
  await expect(page.getByRole("dialog")).toContainText("合成资料：实验室防护与应急流程")
  const downloaded = page.waitForEvent("download")
  await page.getByRole("button", { name: "下载有权原件", exact: true }).click()
  const download = await downloaded, file = await download.path()
  expect(file).toBeTruthy()
  expect(createHash("sha256").update(await fs.readFile(file!)).digest("hex")).toBe(createHash("sha256").update(bytes).digest("hex"))
  await capture(page, "content-real-student-preview")
  await page.getByRole("button", { name: "关闭预览", exact: true }).click()
  await call(request, student, "PATCH", "/content/materials/" + materialId, { revision: 1, title: "不得修改" }, 403)
  const foreign = await token(request, "student_b", "demo-b")
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
