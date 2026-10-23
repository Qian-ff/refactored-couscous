import { expect, test, type APIRequestContext, type Page } from "@playwright/test"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { demoAccounts, reportDirectory } from "../../../others/scripts/web-environment.mjs"

test.use({ trace: "off" }) // Authenticated traces can contain request credentials; screenshots use masked password inputs.
const api = process.env.LABCONNECT_API_URL || "http://127.0.0.1:8000"
const demo = demoAccounts()
const temporary = "DUI-Synthetic-Temporary-Only!"
const password = "DUI-Synthetic-Personal-Only!"
let adminToken: string, schoolId: string, collegeId: string, majorId: string, otherMajor: string, teacherId: string
const unique = (prefix: string) => `${prefix}_${Date.now().toString(36)}_${randomUUID().slice(0, 6)}`
async function call(request: APIRequestContext, method: string, route: string, body?: unknown, token = adminToken, expected = 200) {
  const response = await request.fetch(api + "/api/v1" + route, {
    method, data: body, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), "Idempotency-Key": randomUUID() },
  })
  expect(response.status(), `${method} ${route} status`).toBe(expected)
  return response.json()
}
async function tokenFor(request: APIRequestContext, username: string, value: string) {
  const result = await call(request, "POST", "/auth/login", { school_code: "demo-a", username, password: value }, "")
  return result.access_token as string
}
async function account(request: APIRequestContext, roles = ["student"], forced = false) {
  const username = unique("dui")
  const user = await call(request, "POST", "/admin/accounts", {
    school_id: schoolId, college_id: collegeId, major_id: majorId, username, display_name: "界面合成用户",
    student_no: roles.includes("student") ? unique("DUIS") : null, temporary_password: temporary,
    grants: roles.map(role => ({ role, ...(role === "college_admin" ? { college_id: collegeId } : {}) })),
  }, adminToken, 201)
  if (!forced) {
    const token = await tokenFor(request, username, temporary)
    await call(request, "POST", "/auth/change-password", { old_password: temporary, new_password: password }, token)
  }
  return { ...user, username, password: forced ? temporary : password }
}
async function invitation(request: APIRequestContext, fixed = true, max = 1) {
  return call(request, "POST", "/admin/account-invitations", {
    school_id: schoolId, college_id: collegeId, major_id: fixed ? majorId : null,
    expires_at: new Date(Date.now() + 3600_000).toISOString(), max_uses: max,
  }, adminToken, 201)
}
async function login(page: Page, username: string, value = password, destination = "/") {
  await page.goto("/#" + destination)
  await page.getByLabel("学校代码", { exact: true }).fill("demo-a")
  await page.getByLabel("登录账号", { exact: true }).fill(username)
  await page.getByLabel("登录密码", { exact: true }).fill(value)
  await page.getByRole("button", { name: "登录", exact: true }).click()
}
async function shot(page: Page, name: string, width = 1440) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
  await page.evaluate(() => document.fonts.ready)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
  await page.screenshot({ path: path.join(reportDirectory, `${name}-${width}.png`), fullPage: true })
  if (width === 390) await page.screenshot({ path: path.join(reportDirectory, `${name}-390-first.png`) })
}
async function checkInvite(page: Page, code: string) {
  await page.goto("/#/register")
  await page.getByLabel("学校代码", { exact: true }).fill("demo-a")
  await page.getByLabel("学生账号邀请码", { exact: true }).fill(code)
  await page.getByRole("button", { name: "核验邀请", exact: true }).click()
}
async function fillRegistration(page: Page, username: string) {
  await page.getByLabel("姓名", { exact: true }).fill("注册合成学生")
  await page.getByLabel("学生学号", { exact: true }).fill(unique("REGS"))
  await page.getByLabel("登录账号", { exact: true }).fill(username)
  await page.getByLabel("设置密码", { exact: true }).fill(password)
  await page.getByLabel("确认密码", { exact: true }).fill(password)
}
test.beforeAll(async ({ request }) => {
  adminToken = await tokenFor(request, "admin", demo.password)
  const me = await call(request, "GET", "/auth/me")
  schoolId = me.school.id
  const context = await call(request, "GET", "/courses/context")
  collegeId = context.colleges[0].id
  const teacher = await tokenFor(request, "teacher", demo.password)
  teacherId = (await call(request, "GET", "/auth/me", undefined, teacher)).id
  const majors = []
  for (let i = 0; i < 2; i++) majors.push(await call(request, "POST", "/admin/majors", {
    school_id: schoolId, college_id: collegeId, code: unique("DUI-M"), name: i ? "界面自选专业" : "界面邀请限定专业",
  }, adminToken, 201))
  majorId = majors[0].id; otherMajor = majors[1].id
})

test("三种身份真实登录，B全部注册页面可达，学生越权直链被拒绝", async ({ page }) => {
  for (const [username, title] of [["student", "我的课程"], ["teacher", "我的课程与教学班"], ["admin", "课程与教学班管理"]]) {
    await login(page, username, demo.password)
    await expect(page.getByRole("heading", { level: 1, name: title, exact: true })).toBeVisible()
    if (username === "admin") {
      for (const [label, heading] of [["组织管理", "组织管理"], ["账号与授权", "账号与授权"], ["学生账号邀请", "学生账号邀请"], ["课程与教学班", "课程与教学班管理"]]) {
        await page.getByRole("navigation", { name: "正式导航" }).getByRole("link", { name: label, exact: true }).click()
        await expect(page.getByRole("heading", { level: 1, name: heading, exact: true })).toBeVisible()
      }
      await page.getByRole("button", { name: "管理教学班", exact: true }).first().click()
      await expect(page.getByRole("heading", { name: "学生名单", exact: true })).toBeVisible()
      await expect(page.getByRole("heading", { name: "加入与退出审批", exact: true })).toBeVisible()
      await expect(page.getByRole("heading", { name: "教师协作", exact: true })).toBeVisible()
      await page.goBack()
    }
    if (username === "teacher") {
      await page.getByRole("button", { name: "管理教学班", exact: true }).first().click()
      await expect(page.getByRole("heading", { name: "学生名单", exact: true })).toBeVisible()
      await expect(page.getByRole("heading", { name: "加入与退出审批", exact: true })).toBeVisible()
      await expect(page.getByRole("heading", { name: "教师协作", exact: true })).toBeVisible()
      await page.goBack()
    }
    await expect(page.locator("main")).toHaveCount(1)
    await shot(page, username)
    await page.getByRole("button", { name: "退出登录", exact: true }).click()
    await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  }
  await login(page, "student", demo.password, "/administration/accounts")
  await expect(page.getByRole("heading", { name: "当前身份无权访问" })).toBeVisible()
  await expect(page.getByRole("button", { name: "切换工作身份" })).toHaveCount(0)
  await page.goto("/#/not-a-page")
  await expect(page.getByRole("heading", { name: "页面不存在" })).toBeVisible()
})
test("新账号强制改密，直链不能绕过，旧token失效后重新登录", async ({ page, request }) => {
  const user = await account(request, ["teacher"], true)
  const oldToken = await tokenFor(request, user.username, temporary)
  await login(page, user.username, temporary, "/account/profile")
  await expect(page.getByRole("heading", { name: "首次登录，请修改密码" })).toBeVisible()
  await expect(page.getByRole("navigation", { name: "正式导航" })).toHaveCount(0)
  await shot(page, "first-password")
  await shot(page, "first-password", 390)
  await page.getByLabel("原密码", { exact: true }).fill(temporary)
  await page.getByLabel("新密码", { exact: true }).fill(password)
  await page.getByLabel("确认新密码", { exact: true }).fill(password)
  await page.getByRole("button", { name: "修改密码并重新登录" }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  expect((await request.get(api + "/api/v1/auth/me", { headers: { Authorization: `Bearer ${oldToken}` } })).status()).toBe(401)
  await login(page, user.username)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程与教学班", exact: true })).toBeVisible()
})
test("兼任身份服务端确认、范围收窄、撤权后清理旧页面", async ({ page, request }) => {
  const user = await account(request, ["teacher", "college_admin"])
  await login(page, user.username)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程与教学班", exact: true })).toBeVisible()
  await expect(page.getByRole("link", { name: "组织管理", exact: true })).toHaveCount(0)
  await expect(page.getByText("当前条件下没有获授权教学班。", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "切换工作身份" }).click()
  await shot(page, "identity-dialog")
  await shot(page, "identity-dialog", 390)
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByRole("dialog").getByRole("button", { name: "管理员", exact: true }).click()
  await expect(page.getByRole("navigation", { name: "正式导航" }).getByRole("link", { name: "组织管理", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "管理教学班", exact: true }).first()).toBeVisible()
  await page.getByRole("button", { name: "切换工作身份" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "教师", exact: true }).click()
  await expect(page.getByRole("link", { name: "组织管理", exact: true })).toHaveCount(0)
  await call(request, "POST", `/admin/accounts/${user.id}/revoke-grant`, { role: "teacher" })
  await page.evaluate(() => window.dispatchEvent(new Event("focus")))
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await expect(page.locator(".b1-ui")).toHaveCount(0)
})
test("学生邀请注册、合法专业、重复点击及注册后手动登录", async ({ page, request }) => {
  const invite = await invitation(request)
  const username = unique("dui_reg")
  await call(request, "POST", "/auth/register", { school_code: "demo-a", invitation_code: invite.code, username: unique("dui_illegal_major"), student_no: unique("ILLEGAL"),
    display_name: "合成越界注册", password, major_id: otherMajor }, "", 422)
  let submissions = 0
  page.on("request", r => { if (r.url().endsWith("/auth/register")) submissions++ })
  await checkInvite(page, invite.code)
  await expect(page.getByLabel("专业", { exact: true }).locator("option:not([disabled])")).toHaveCount(1)
  await fillRegistration(page, username)
  await shot(page, "registration")
  await shot(page, "registration", 390)
  await page.getByRole("button", { name: "开通学生账号", exact: true }).evaluate((el: HTMLButtonElement) => { el.click(); el.click() })
  await expect(page.getByRole("heading", { name: "学生账号已开通" })).toBeVisible()
  expect(submissions).toBe(1)
  await expect(page.getByRole("navigation", { name: "正式导航" })).toHaveCount(0)
  await expect(page.getByText("账号已开通，尚未登录。", { exact: false })).toBeVisible()
  await login(page, username)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  await checkInvite(page, invite.code)
  await expect(page.getByRole("alert")).toContainText("已失效或使用次数已满")
})
test("无效、撤销和过期邀请，未限定专业只能使用接口合法选项", async ({ page, request }) => {
  await checkInvite(page, "invalid-invitation-code")
  await expect(page.getByRole("alert")).toBeVisible()
  const revoked = await invitation(request)
  await call(request, "POST", `/admin/account-invitations/${revoked.id}/revoke`, {})
  await checkInvite(page, revoked.code)
  await expect(page.getByRole("alert")).toContainText("已失效")
  const expires = await call(request, "POST", "/admin/account-invitations", {
    school_id: schoolId, college_id: collegeId, major_id: majorId, expires_at: new Date(Date.now() + 1500).toISOString(), max_uses: 1,
  }, adminToken, 201)
  await expect.poll(async () => (await request.get(api + "/api/v1/auth/invitations/" + expires.code + "?school_code=demo-a")).status()).toBe(422)
  await checkInvite(page, expires.code)
  await expect(page.getByRole("alert")).toContainText("已失效")
  const open = await invitation(request, false)
  await checkInvite(page, open.code)
  await expect(page.getByLabel("专业", { exact: true }).locator(`option[value="${otherMajor}"]`)).toHaveCount(1)
  await fillRegistration(page, unique("dui_open"))
  await page.getByLabel("专业", { exact: true }).selectOption(otherMajor)
  await page.getByRole("button", { name: "开通学生账号", exact: true }).click()
  await expect(page.getByRole("heading", { name: "学生账号已开通" })).toBeVisible()
})
test("本人资料只改合法字段，revision冲突重新读取，普通改密清理会话", async ({ page, request }) => {
  const user = await account(request)
  const token = await tokenFor(request, user.username, password)
  await login(page, user.username, password, "/account/profile")
  await expect(page.getByRole("heading", { level: 1, name: "本人资料", exact: true })).toBeVisible()
  await expect(page.locator('input[name="username"],input[name="student_no"],input[name="school"]')).toHaveCount(0)
  const profile = await call(request, "GET", "/profile", undefined, token)
  await call(request, "PATCH", "/profile", { revision: profile.revision, contact: "合成并发更新" }, token)
  await page.getByLabel("联系方式（选填）", { exact: true }).fill("界面待保存")
  await page.getByRole("button", { name: "保存本人资料" }).click()
  await expect(page.getByText("资料已被更新，已重新读取最新版本。请核对后再次保存。")).toBeVisible()
  await expect(page.getByLabel("联系方式（选填）", { exact: true })).toHaveValue("合成并发更新")
  await page.getByLabel("联系方式（选填）", { exact: true }).fill("界面真实保存")
  await page.getByRole("button", { name: "保存本人资料" }).click()
  await expect(page.getByText("本人资料已保存", { exact: true })).toBeVisible()
  expect((await call(request, "GET", "/profile", undefined, token)).contact).toBe("界面真实保存")
  const current = await call(request, "GET", "/profile", undefined, token)
  const illegal = await request.patch(api + "/api/v1/profile", { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": randomUUID() }, data: { revision: current.revision, display_name: "不应修改" } })
  expect(illegal.status()).toBe(422)
  await shot(page, "profile")
  await shot(page, "profile", 390)
  await page.getByRole("link", { name: "修改密码", exact: true }).click()
  await page.getByLabel("原密码", { exact: true }).fill(password)
  await page.getByLabel("新密码", { exact: true }).fill(password + "Next")
  await page.getByLabel("确认新密码", { exact: true }).fill(password + "Next")
  await page.getByRole("button", { name: "修改密码并重新登录" }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
})
test("学生课程真实分页搜索、移动导航、长内容和刷新重登直链", async ({ page, request }) => {
  test.setTimeout(120_000)
  const user = await account(request)
  const prefix = unique("DUIC")
  for (let i = 0; i < 13; i++) {
    const course = await call(request, "POST", "/courses", { college_id: collegeId, teacher_id: teacherId, code: `${prefix}-${i}`,
      title: `界面课程检索${i}：实验室规范与跨学院协同的长标题布局验证` }, adminToken, 201)
    await call(request, "POST", `/courses/${course.id}/members`, { username: user.username })
  }
  await login(page, user.username)
  await expect(page.locator(".lc-course-card")).toHaveCount(12)
  await expect(page.getByTestId("course-count")).toHaveText("13")
  await page.getByRole("button", { name: "下一页", exact: true }).click()
  await expect(page.locator(".lc-course-card")).toHaveCount(1)
  await page.getByLabel("搜索课程", { exact: true }).fill("界面课程检索12")
  await page.getByRole("button", { name: "搜索", exact: true }).click()
  await expect(page.getByTestId("course-count")).toHaveText("1")
  await page.getByRole("button", { name: "清空", exact: true }).click()
  await expect(page.locator(".lc-course-card")).toHaveCount(12)
  await shot(page, "student-courses")
  await shot(page, "student-courses", 390)
  await page.getByRole("button", { name: "打开导航菜单" }).click()
  await expect(page.getByRole("dialog")).toBeVisible()
  await page.getByRole("dialog").getByRole("link", { name: "本人资料", exact: true }).click()
  await expect(page.getByRole("heading", { level: 1, name: "本人资料", exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await page.getByLabel("登录账号", { exact: true }).fill(user.username)
  await page.getByLabel("登录密码", { exact: true }).fill(password)
  await page.getByRole("button", { name: "登录", exact: true }).click()
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
})
test("对话框键盘焦点、离线状态、远端退出失败仍清理本地", async ({ page, context }) => {
  await page.goto("/")
  await shot(page, "login")
  await shot(page, "login", 390)
  const trigger = page.getByRole("button", { name: "连接设置", exact: true })
  await trigger.click()
  const dialog = page.getByRole("dialog")
  for (let i = 0; i < 7; i++) {
    await page.keyboard.press("Tab")
    expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBeTruthy()
  }
  await page.keyboard.press("Escape")
  await expect(trigger).toBeFocused()
  await login(page, "student", demo.password)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  await context.setOffline(true)
  await expect(page.getByText("网络已断开。", { exact: false })).toBeVisible()
  await shot(page, "offline", 390)
  await context.setOffline(false)
  await page.route("**/api/v1/auth/logout", route => route.abort("failed"))
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await expect(page.getByText("本机已退出；远端注销未确认，请联系管理员撤销旧会话。")).toBeVisible()
})
test("401与服务地址变化清理身份，迟到课程响应不能回填登录页", async ({ page, request }) => {
  const user = await account(request)
  await login(page, user.username)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  await call(request, "POST", `/admin/accounts/${user.id}/reset-password`, { temporary_password: temporary })
  await page.getByRole("button", { name: "刷新", exact: true }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await login(page, "student", demo.password)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  let release!: () => void, fetched!: () => void
  const held = new Promise<void>(resolve => { release = resolve }), ready = new Promise<void>(resolve => { fetched = resolve })
  await page.route("**/api/v1/courses?**", async route => {
    const response = await route.fetch(); fetched(); await held
    await route.fulfill({ response }).catch(() => {})
  })
  await page.getByRole("button", { name: "刷新", exact: true }).click()
  await ready
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  release()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
  await expect(page.locator(".lc-course-card")).toHaveCount(0)
  await page.unroute("**/api/v1/courses?**")
  await login(page, "student", demo.password)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "服务连接设置", exact: true }).click()
  await page.getByLabel("服务地址", { exact: true }).fill("http://localhost:8000")
  await page.getByRole("button", { name: "保存连接设置", exact: true }).click()
  await expect(page.getByRole("heading", { name: "欢迎使用安研通" })).toBeVisible()
})



test("同身份中文输入与查询竞态、真实失败重试和注册同键恢复", async ({ page, request }) => {
  await login(page, "student", demo.password)
  await expect(page.getByRole("heading", { level: 1, name: "我的课程", exact: true })).toBeVisible()
  const count = await page.getByTestId("course-count").textContent()
  const search = page.getByLabel("搜索课程", { exact: true })
  let requests = 0
  page.on("request", r => { if (r.url().includes("/api/v1/courses?")) requests++ })
  await search.dispatchEvent("compositionstart")
  await search.fill("尚在拼音输入")
  await search.press("Enter")
  expect(requests).toBe(0)
  await search.dispatchEvent("compositionend")
  let release!: () => void, fetched!: () => void
  const held = new Promise<void>(r => { release = r }), ready = new Promise<void>(r => { fetched = r })
  await page.route("**/api/v1/courses?**", async route => {
    if (new URL(route.request().url()).searchParams.get("q") === "尚在拼音输入") {
      const response = await route.fetch(); fetched(); await held; await route.fulfill({ response }).catch(() => {})
    } else await route.continue()
  })
  await page.getByRole("button", { name: "搜索", exact: true }).click()
  await ready
  await page.getByRole("button", { name: "清空", exact: true }).click()
  await expect(page.getByTestId("course-count")).toHaveText(count!)
  release()
  await expect(page.getByTestId("course-count")).toHaveText(count!)
  await page.unroute("**/api/v1/courses?**")
  await page.route("**/api/v1/courses?**", route => route.abort("failed"))
  await page.getByRole("button", { name: "刷新", exact: true }).click()
  await expect(page.getByRole("heading", { name: "读取失败", exact: true })).toBeVisible()
  await page.unroute("**/api/v1/courses?**")
  await page.getByRole("button", { name: "重新读取", exact: true }).click()
  await expect(page.getByTestId("course-count")).toHaveText(count!)
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  const invite = await invitation(request)
  await checkInvite(page, invite.code)
  await fillRegistration(page, unique("dui_uncertain"))
  let key: string | undefined, calls = 0
  await page.route("**/api/v1/auth/register", async route => {
    const current = route.request().headers()["idempotency-key"]
    if (!key) key = current
    else expect(current === key, "Retry must reuse the uncertain registration key").toBeTruthy()
    const response = await route.fetch()
    if (++calls === 1) await route.abort("failed")
    else await route.fulfill({ response })
  })
  await page.getByRole("button", { name: "开通学生账号", exact: true }).click()
  await expect(page.getByRole("alert")).toContainText("无法连接服务")
  await page.getByRole("button", { name: "开通学生账号", exact: true }).click()
  await expect(page.getByRole("heading", { name: "学生账号已开通" })).toBeVisible()
  expect(calls).toBe(2)
})

test.describe("手机触控", () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } })
  test("真实学生触控打开导航与本人资料，未开放功能保持禁用", async ({ page, request }) => {
    const user = await account(request)
    await login(page, user.username)
    await expect(page.getByRole("heading", { name: "我的课程", exact: true, level: 1 })).toBeVisible()
    await page.getByRole("button", { name: "打开导航菜单" }).tap()
    await page.getByRole("dialog").getByRole("link", { name: "本人资料", exact: true }).tap()
    await expect(page.getByRole("heading", { name: "本人资料", exact: true, level: 1 })).toBeVisible()
    await page.getByLabel("联系方式（选填）", { exact: true }).tap()
    await page.getByLabel("联系方式（选填）", { exact: true }).fill("触控合成资料")
    await page.getByRole("button", { name: "保存本人资料" }).tap()
    await expect(page.getByText("本人资料已保存", { exact: true })).toBeVisible()
    await expect(page.getByRole("navigation", { name: "学生快捷导航" }).getByRole("button", { name: /学习助手/ })).toBeDisabled()
    await shot(page, "touch-profile", 390)
  })
})
