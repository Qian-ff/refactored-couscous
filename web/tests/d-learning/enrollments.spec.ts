import { expect, test, type APIRequestContext, type Page } from "@playwright/test"
import { randomUUID } from "node:crypto"
import path from "node:path"
import { demoAccounts, reportDirectory } from "../../../others/scripts/web-environment.mjs"

test.use({ trace: "off" })
const api = process.env.LABCONNECT_API_URL || "http://127.0.0.1:8000"
const demo = demoAccounts()
const temporary = "D-Enrollment-Synthetic-Temporary!"
const personal = "D-Enrollment-Synthetic-Personal!"
let admin: string, school: string, college: string, teacher: string
const unique = (prefix: string) => prefix + "_" + Date.now().toString(36) + "_" + randomUUID().slice(0, 5)
const testOrigins = new WeakMap<object, Set<string>>()
async function call(request: APIRequestContext, method: string, route: string, data?: unknown, token = admin, status = 200) {
  const response = await request.fetch(api + "/api/v1" + route, { method, data, headers: { Authorization: "Bearer " + token, "Idempotency-Key": randomUUID() } })
  expect(response.status(), method + " " + route).toBe(status)
  return response.json()
}
async function loginToken(request: APIRequestContext, username: string, password: string, schoolCode = "demo-a") {
  return (await call(request, "POST", "/auth/login", { school_code: schoolCode, username, password }, "")).access_token as string
}
async function student(request: APIRequestContext) {
  const username = unique("drel")
  const record = await call(request, "POST", "/admin/accounts", {
    school_id: school, college_id: college, username, student_no: unique("DREL"), display_name: "班级关系合成学生",
    temporary_password: temporary, grants: [{ role: "student" }],
  }, admin, 201)
  const first = await loginToken(request, username, temporary)
  await call(request, "POST", "/auth/change-password", { old_password: temporary, new_password: personal }, first)
  return { ...record, username, token: await loginToken(request, username, personal) }
}
async function classroom(request: APIRequestContext, joinApproval = false, leaveApproval = false) {
  const record = await call(request, "POST", "/courses", { college_id: college, teacher_id: teacher, code: unique("DREL"), title: "学生班级关系验证：实验室安全与跨学院协同" }, admin, 201)
  const management = await call(request, "GET", "/courses/" + record.id + "/management")
  const settings = await call(request, "PATCH", "/courses/" + record.id + "/settings", { revision: management.revision, join_approval: joinApproval, leave_approval: leaveApproval })
  const invite = await call(request, "POST", "/courses/" + record.id + "/invite", { revision: settings.revision, expires_at: new Date(Date.now() + 3600_000).toISOString() })
  return { ...record, invite: invite.code }
}
async function enter(page: Page, user: { username: string }, destination = "/student/courses") {
  await page.addInitScript(url => localStorage.setItem("safelab.service", url), api)
  await page.goto("/#" + destination)
  await page.getByLabel("学校代码", { exact: true }).fill("demo-a")
  await page.getByLabel("登录账号", { exact: true }).fill(user.username)
  await page.getByLabel("登录密码", { exact: true }).fill(personal)
  await page.getByRole("button", { name: "登录", exact: true }).click()
}
async function join(page: Page, code: string) {
  await page.getByRole("button", { name: "使用班级邀请码加入", exact: true }).click()
  await page.getByLabel("班级邀请码", { exact: true }).fill(code)
  await page.getByRole("dialog").getByRole("button", { name: "确认加入教学班", exact: true }).click()
}
async function viewRequests(page: Page) {
  await page.goto("/#/student/enrollments")
  await expect(page.getByRole("heading", { level: 1, name: "班级申请与历史", exact: true })).toBeVisible()
}
async function capture(page: Page, name: string) {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
    await page.evaluate(() => document.fonts.ready)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
    const tooSmall = await page.locator(".lc-page .lc-button:visible,dialog .lc-button:visible").evaluateAll(nodes => nodes.filter(el => { const r = el.getBoundingClientRect(); return r.width < 43.5 || r.height < 43.5 }).length)
    expect(tooSmall).toBe(0)
    await page.screenshot({ path: path.join(reportDirectory, name + "-" + width + ".png"), fullPage: true, mask: [page.locator('textarea[name="class-code"]')] })
    if (width === 390) await page.screenshot({ path: path.join(reportDirectory, name + "-390-first.png"), mask: [page.locator('textarea[name="class-code"]')] })
  }
  await page.setViewportSize({ width: 1440, height: 1000 })
}
test.beforeAll(async ({ request }) => {
  admin = await loginToken(request, "admin", demo.password)
  school = (await call(request, "GET", "/auth/me")).school.id
  college = (await call(request, "GET", "/courses/context")).colleges[0].id
  const teacherToken = await loginToken(request, "teacher", demo.password)
  teacher = (await call(request, "GET", "/auth/me", undefined, teacherToken)).id
})
test.beforeEach(async ({ page }, info) => {
  const origins = new Set<string>()
  page.on("request", request => { if (request.url().includes("/api/v1/")) origins.add(new URL(request.url()).origin) })
  test.info().annotations.push({ type: "surface", description: "Formal HashRouter; real API only" })
  // Keep only API origins in evidence, never credentials, query values, invitation codes or payloads.
  await info.attach("expected-api-origin", { body: new URL(api).origin, contentType: "text/plain" })
  testOrigins.set(info, origins)
})
test.afterEach(async ({}, info) => {
  const origins = [...(testOrigins.get(info) || [])]
  await info.attach("actual-api-origins", { body: JSON.stringify(origins), contentType: "application/json" })
  expect(origins.length).toBeGreaterThan(0)
  expect(origins.every(origin => origin === new URL(api).origin)).toBeTruthy()
})

test("直接加入和退出，重复加入不重复建关系，退班旧直链无权", async ({ page, request }) => {
  const user = await student(request), course = await classroom(request)
  await enter(page, user)
  await join(page, course.invite)
  await expect(page.getByText("服务端已确认当前在班。", { exact: false })).toBeVisible()
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  await join(page, course.invite)
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  const members = await call(request, "GET", "/courses/" + course.id + "/members")
  expect(members.data.filter((row: { id: string }) => row.id === user.id)).toHaveLength(1)
  await capture(page, "enrolled-course")
  await page.getByRole("link", { name: "查看班级", exact: true }).click()
  await expect(page.getByRole("heading", { level: 1, name: course.title, exact: true })).toBeVisible()
  await page.getByRole("button", { name: "退出教学班", exact: true }).click()
  await capture(page, "leave-dialog")
  await page.getByRole("dialog").getByRole("button", { name: "确认退出教学班" }).click()
  await expect(page.getByText("服务端已确认退出教学班", { exact: false })).toBeVisible()
  await expect(page.getByRole("heading", { name: "教学班当前不可访问", exact: true })).toBeVisible()
  expect((await request.get(api + "/api/v1/courses/" + course.id, { headers: { Authorization: "Bearer " + user.token } })).status()).toBe(404)
  await page.reload()
  await enter(page, user, "/student/courses/" + course.id)
  await expect(page.getByRole("heading", { name: "教学班当前不可访问" })).toBeVisible()
})
test("加入审批、重复申请、撤销与批准后刷新，退出审批先保留当前关系", async ({ page, request }) => {
  const user = await student(request), course = await classroom(request, true, true)
  await enter(page, user)
  await join(page, course.invite)
  await expect(page.getByText("加入申请待审批", { exact: false })).toBeVisible()
  await join(page, course.invite)
  expect((await call(request, "GET", "/enrollments/requests", undefined, user.token)).count).toBe(1)
  await viewRequests(page)
  await expect(page.getByText("待审批", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "撤销申请", exact: true }).click()
  await page.getByRole("button", { name: "确认撤销申请", exact: true }).click()
  await expect(page.getByText("已撤销", { exact: true })).toBeVisible()
  await join(page, course.invite)
  const pending = (await call(request, "GET", "/enrollments/requests", undefined, user.token)).data.find((r: { status: string }) => r.status === "pending")
  await call(request, "POST", "/courses/" + course.id + "/requests/" + pending.id + "/decide", { approve: true })
  await page.getByRole("button", { name: "刷新申请状态" }).click()
  await expect(page.getByText("已批准", { exact: true })).toBeVisible()
  await page.goto("/#/student/courses")
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  await page.getByRole("button", { name: "退出教学班", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "确认退出教学班" }).click()
  await expect(page.getByText("退出申请待审批", { exact: false })).toBeVisible()
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  await viewRequests(page)
  const leave = (await call(request, "GET", "/enrollments/requests", undefined, user.token)).data.find((r: { kind: string; status: string }) => r.kind === "leave" && r.status === "pending")
  await call(request, "POST", "/courses/" + course.id + "/requests/" + leave.id + "/decide", { approve: true })
  await page.getByRole("button", { name: "刷新申请状态" }).click()
  await page.goto("/#/student/courses")
  await expect(page.locator(".lc-course-card")).toHaveCount(0)
})
test("撤销与教师审批并发冲突，拒绝结果真实显示，不扩大学生读取范围", async ({ page, request }) => {
  const user = await student(request), other = await student(request), course = await classroom(request, true)
  await enter(page, user)
  await join(page, course.invite)
  await viewRequests(page)
  const pending = (await call(request, "GET", "/enrollments/requests", undefined, user.token)).data[0]
  await page.getByRole("button", { name: "撤销申请", exact: true }).click()
  await call(request, "POST", "/courses/" + course.id + "/requests/" + pending.id + "/decide", { approve: false })
  await page.getByRole("button", { name: "确认撤销申请", exact: true }).click()
  await expect(page.getByText("申请状态已变化", { exact: false })).toBeVisible()
  await expect(page.getByText("未批准", { exact: true })).toBeVisible()
  expect((await call(request, "GET", "/enrollments/requests", undefined, other.token)).count).toBe(0)
  await call(request, "POST", "/enrollments/requests/" + pending.id + "/cancel", {}, other.token, 404)
  for (const suffix of ["/members", "/management", "/requests"]) expect((await request.get(api + "/api/v1/courses/" + course.id + suffix, { headers: { Authorization: "Bearer " + user.token } })).status()).toBeGreaterThanOrEqual(403)
  await capture(page, "request-conflict")
})
test("邀请码无效、轮换、过期与跨校拒绝，长代码和离线失败可重试", async ({ page, context, request }) => {
  const user = await student(request), course = await classroom(request)
  await enter(page, user)
  await join(page, "invalid-class-code-" + "x".repeat(70))
  await expect(page.getByRole("alert")).toContainText("无效或已过期")
  await capture(page, "invalid-long-code")
  const management = await call(request, "GET", "/courses/" + course.id + "/management")
  const expiresAt = Date.now() + 1500
  const rotated = await call(request, "POST", "/courses/" + course.id + "/invite", { revision: management.revision, expires_at: new Date(expiresAt).toISOString() })
  await page.getByLabel("班级邀请码", { exact: true }).fill(course.invite)
  await page.getByRole("button", { name: "确认加入教学班" }).click()
  await expect(page.getByRole("alert")).toContainText("无效或已过期")
  await expect.poll(() => Date.now() >= expiresAt).toBeTruthy()
  await page.getByLabel("班级邀请码", { exact: true }).fill(rotated.code)
  await page.getByRole("button", { name: "确认加入教学班" }).click()
  await expect(page.getByRole("alert")).toContainText("无效或已过期")
  const foreignAdmin = await loginToken(request, "admin_b", demo.password, "demo-b")
  const foreignTeacher = await loginToken(request, "teacher_b", demo.password, "demo-b")
  const foreignCollege = (await call(request, "GET", "/courses/context", undefined, foreignAdmin)).colleges[0].id
  const foreignTeacherId = (await call(request, "GET", "/auth/me", undefined, foreignTeacher)).id
  const foreignCourse = await call(request, "POST", "/courses", { college_id: foreignCollege, teacher_id: foreignTeacherId, code: unique("DRELB"), title: "隔离学校合成班级" }, foreignAdmin, 201)
  const foreignManagement = await call(request, "GET", "/courses/" + foreignCourse.id + "/management", undefined, foreignAdmin)
  const foreignInvite = await call(request, "POST", "/courses/" + foreignCourse.id + "/invite", { revision: foreignManagement.revision, expires_at: new Date(Date.now() + 3600_000).toISOString() }, foreignAdmin)
  await page.getByLabel("班级邀请码", { exact: true }).fill(foreignInvite.code)
  await page.getByRole("button", { name: "确认加入教学班" }).click()
  await expect(page.getByRole("alert")).toContainText("无效或已过期")
  await context.setOffline(true)
  await page.getByRole("button", { name: "确认加入教学班" }).click()
  await expect(page.getByRole("alert")).toContainText("无法连接服务")
  await context.setOffline(false)
  await page.getByRole("button", { name: "取消", exact: true }).click()
  await expect(page.locator(".lc-course-card")).toHaveCount(0)
})
test("退出响应丢失复用原幂等键，旧查询与退出会话不能回填", async ({ page, request }) => {
  const user = await student(request), course = await classroom(request)
  await call(request, "POST", "/enrollments/join", { invitation_code: course.invite }, user.token)
  await enter(page, user)
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  let calls = 0, key: string | undefined
  await page.route("**/api/v1/courses/" + course.id + "/leave", async route => {
    const current = route.request().headers()["idempotency-key"]
    if (!key) key = current; else expect(current === key).toBeTruthy()
    const response = await route.fetch()
    if (++calls === 1) await route.abort("failed"); else await route.fulfill({ response })
  })
  await page.getByRole("button", { name: "退出教学班", exact: true }).click()
  await page.getByRole("button", { name: "确认退出教学班" }).click()
  await expect(page.getByRole("alert")).toContainText("无法连接服务")
  await page.getByRole("button", { name: "确认退出教学班" }).click()
  await expect(page.locator(".lc-course-card")).toHaveCount(0)
  expect(calls).toBe(2)
})
test("移出、归档及撤权后旧班级页面清理，历史不授予当前权限", async ({ page, request }) => {
  const user = await student(request), course = await classroom(request)
  await call(request, "POST", "/enrollments/join", { invitation_code: course.invite }, user.token)
  await enter(page, user, "/student/courses/" + course.id)
  await expect(page.getByRole("heading", { name: course.title, level: 1 })).toBeVisible()
  await call(request, "POST", "/courses/" + course.id + "/remove-member", { username: user.username })
  await page.getByRole("button", { name: "刷新班级状态" }).click()
  await expect(page.getByRole("heading", { name: "教学班当前不可访问" })).toBeVisible()
  await call(request, "POST", "/enrollments/join", { invitation_code: course.invite }, user.token)
  await page.getByRole("button", { name: "重新读取" }).click()
  await expect(page.getByRole("heading", { name: course.title, level: 1 })).toBeVisible()
  const management = await call(request, "GET", "/courses/" + course.id + "/management")
  await call(request, "POST", "/courses/" + course.id + "/archive", { revision: management.revision })
  await page.getByRole("button", { name: "刷新班级状态" }).click()
  await expect(page.getByRole("heading", { name: "教学班当前不可访问" })).toBeVisible()
  await call(request, "POST", "/admin/accounts/" + user.id + "/revoke-grant", { role: "student" })
  await page.evaluate(() => window.dispatchEvent(new Event("focus")))
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
})
test("本人申请分页与手机长列表，清空会话后不能保留记录", async ({ page, request }) => {
  test.setTimeout(120_000)
  const user = await student(request), course = await classroom(request, true)
  for (let i = 0; i < 21; i++) {
    const result = await call(request, "POST", "/enrollments/join", { invitation_code: course.invite }, user.token)
    if (i < 20) await call(request, "POST", "/enrollments/requests/" + result.request_id + "/cancel", {}, user.token)
  }
  await enter(page, user, "/student/enrollments")
  await expect(page.locator(".lc-records>li")).toHaveCount(20)
  await page.getByRole("button", { name: "下一页", exact: true }).click()
  await expect(page.locator(".lc-records>li")).toHaveCount(1)
  await page.getByRole("button", { name: "上一页", exact: true }).click()
  await capture(page, "requests-long-list")
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await expect(page.locator(".lc-records>li")).toHaveCount(0)
})
test.describe("学生班级触控", () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } })
  test("手机使用班级邀请码提交并撤销本人申请", async ({ page, request }) => {
    const user = await student(request), course = await classroom(request, true)
    await enter(page, user)
    await expect(page.getByRole("heading", { name: "我的课程", level: 1 })).toBeVisible()
    await page.getByRole("button", { name: "打开导航菜单" }).tap()
    await page.getByRole("dialog").getByRole("link", { name: "班级申请与历史", exact: true }).tap()
    await page.getByRole("button", { name: "使用班级邀请码加入", exact: true }).tap()
    await page.getByLabel("班级邀请码", { exact: true }).tap()
    await page.getByLabel("班级邀请码", { exact: true }).fill(course.invite)
    await page.getByRole("button", { name: "确认加入教学班", exact: true }).tap()
    await expect(page.getByText("待审批", { exact: true })).toBeVisible()
    await page.getByRole("button", { name: "撤销申请", exact: true }).tap()
    await page.getByRole("button", { name: "确认撤销申请", exact: true }).tap()
    await expect(page.getByText("已撤销", { exact: true })).toBeVisible()
    await capture(page, "touch-request-canceled")
  })
})
