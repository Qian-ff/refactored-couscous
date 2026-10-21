import path from "node:path"
import { randomUUID } from "node:crypto"
import { expect, test, type Page } from "@playwright/test"
import { demoAccounts } from "../../../../../../others/scripts/web-environment.mjs"

const api = process.env.LABCONNECT_API_URL || "http://127.0.0.1:8001"
const entry = `/src/features/teaching/dev/index.html?api=${encodeURIComponent(api)}`
const demo = demoAccounts()
const temporary = "B1-Synthetic-Temporary-Only!"
function unique(prefix: string) { return `${prefix}_${Date.now().toString(36)}_${randomUUID().slice(0, 5)}` }
function section(page: Page, title: string) { return page.getByRole("heading", { name: title, exact: true }).locator("xpath=ancestor::section[1]") }
async function signIn(page: Page, username: string, password = demo.password) {
  await page.goto(entry)
  await page.getByLabel("学校代码", { exact: true }).fill("demo-a")
  await page.getByLabel("登录账号", { exact: true }).fill(username)
  await page.getByLabel("登录密码", { exact: true }).fill(password)
  await page.getByRole("button", { name: "进入组件夹具", exact: true }).click()
  await expect(page.getByRole("heading", { name: "连接真实服务", exact: true })).toHaveCount(0)
}
async function nav(page: Page, name: string) {
  await page.getByRole("navigation", { name: "B1 组件选择" }).getByRole("button", { name, exact: true }).click()
}

test("组织、账号、首次改密与真实兼任身份收窄", async ({ page }) => {
  test.setTimeout(120_000)
  const code = unique("MAJOR")
  const username = unique("b1_ui_teacher")
  const displayName = `合成教员${code.slice(-5)}`
  await signIn(page, "admin")
  await nav(page, "组织管理")
  await page.getByRole("button", { name: "专业管理", exact: true }).click()
  const createMajor = section(page, "创建专业")
  await createMajor.getByLabel(/^代码/).fill(code)
  await createMajor.getByLabel("专业名称", { exact: true }).fill(`界面合成专业${code}`)
  await createMajor.getByRole("button", { name: "确认创建", exact: true }).click()
  await expect(page.getByText("组织已创建", { exact: true })).toBeVisible()
  await nav(page, "账号与授权")
  await page.getByRole("button", { name: "新建账号", exact: true }).click()
  const create = section(page, "创建账号")
  await create.getByLabel("教师", { exact: true }).check()
  await expect(create.getByLabel("学生", { exact: true })).not.toBeChecked()
  await create.getByLabel(/^登录账号/).fill(username)
  await create.getByLabel("姓名", { exact: true }).fill(displayName)
  await create.getByLabel(/^初始临时密码/).fill(temporary)
  await create.getByRole("button", { name: "创建账号", exact: true }).click()
  await expect(page.getByText("账号已开通，首次登录须修改临时密码", { exact: true })).toBeVisible()
  const grants = section(page, "角色授权")
  await grants.getByLabel("新增角色", { exact: true }).selectOption("college_admin")
  await grants.getByLabel("学院管理员授权范围", { exact: true }).selectOption({ label: "化学学院" })
  await grants.getByRole("button", { name: "添加授权", exact: true }).click()
  await expect(page.getByText("角色授权已保存", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "退出登录", exact: true }).click()
  await signIn(page, username, temporary)
  await expect(page.getByRole("heading", { name: "首次登录请修改密码", exact: true })).toBeVisible()
  await page.getByLabel("原临时密码", { exact: true }).fill(temporary)
  await page.getByLabel("新密码", { exact: true }).fill(temporary + "-changed")
  await page.getByRole("button", { name: "修改密码并重新登录", exact: true }).click()
  await expect(page.getByRole("heading", { name: "连接真实服务", exact: true })).toBeVisible()
  await signIn(page, username, temporary + "-changed")
  await expect(page.getByLabel("当前工作身份", { exact: true })).toHaveValue("teacher")
  await expect(page.getByRole("heading", { name: "我的课程与教学班", exact: true })).toBeVisible()
  await page.getByLabel("当前工作身份", { exact: true }).selectOption("administrator")
  await expect(page.getByRole("heading", { name: "账号与授权", exact: true })).toBeVisible()
  await page.getByLabel("CSV 内容", { exact: false }).fill("sensitive-old-scope-content")
  await page.getByLabel("当前工作身份", { exact: true }).selectOption("teacher")
  await expect(page.getByRole("heading", { name: "我的课程与教学班", exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "账号与授权", exact: true })).toHaveCount(0)
  await expect(page.getByLabel("CSV 内容", { exact: false })).toHaveCount(0)
  const denied = await page.evaluate(async () => {
    const modulePath = "/src/client/index.ts"
    const { ManagementService } = await import(modulePath)
    try { await ManagementService.listAccounts(); return 200 } catch (error: any) { return error.response?.status }
  })
  expect(denied).toBe(403)
})

test("CSV 逐行预检、全量提交与响应丢失后的幂等重试", async ({ page }) => {
  const name = unique("b1_csv")
  await signIn(page, "admin")
  const importer = section(page, "批量开通账号")
  const header = "username,student_no,display_name,college_code,major_code,role,temporary_password,gender,contact\n"
  const row = `${name},,合成CSV教员,chem,,teacher,${temporary},,\n`
  await importer.getByLabel("CSV 内容", { exact: false }).fill(header + row + row)
  await importer.getByRole("button", { name: "预检文件", exact: true }).click()
  await expect(importer.getByText("文件内重复", { exact: true })).toBeVisible()
  await expect(importer.getByRole("button", { name: /^确认整批提交/ })).toBeDisabled()
  await importer.getByLabel("CSV 内容", { exact: false }).fill(header + row)
  await importer.getByRole("button", { name: "预检文件", exact: true }).click()
  await expect(importer.getByRole("button", { name: "确认整批提交（1 行）", exact: true })).toBeEnabled()
  let lost = false
  const keys: string[] = []
  await page.route("**/api/v1/imports/commit", async route => {
    if (route.request().method() !== "POST") return route.continue()
    keys.push(route.request().headers()["idempotency-key"])
    if (!lost) { lost = true; await route.fetch(); await route.abort("failed") }
    else await route.continue()
  })
  await importer.getByRole("button", { name: "确认整批提交（1 行）", exact: true }).click()
  await expect(importer.getByRole("alert")).toContainText("无法连接服务")
  await importer.getByRole("button", { name: "确认整批提交（1 行）", exact: true }).click()
  await expect(importer.getByText("整批提交成功", { exact: true })).toBeVisible()
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBe(keys[1])
  await page.getByLabel("账号、姓名或学号", { exact: true }).fill(name)
  await page.getByRole("button", { name: "查询账号", exact: true }).click()
  await expect(section(page, "授权范围内的账号").getByText(name, { exact: true })).toBeVisible()
  await expect(section(page, "授权范围内的账号").getByText(/共 1 项/)).toBeVisible()
})

test("教师班级真实名单、审批、协作、交接和归档", async ({ page, context, request }) => {
  test.setTimeout(150_000)
  const code = unique("CLASS")
  const title = `界面合成班${code.slice(-6)}`
  await signIn(page, "teacher")
  await page.getByRole("button", { name: "新建课程与首班", exact: true }).click()
  const creating = section(page, "新建课程目录与首班")
  await creating.getByLabel("目录与首班代码", { exact: true }).fill(code)
  await creating.getByLabel("课程与首班名称", { exact: true }).fill(title)
  const creationResponse = page.waitForResponse(response => response.url().endsWith("/api/v1/courses") && response.request().method() === "POST")
  await creating.getByRole("button", { name: "确认创建教学班", exact: true }).click()
  const course = await (await creationResponse).json()
  await page.getByRole("button", { name: "进入新教学班", exact: true }).click()
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible()
  const settings = section(page, "班级设置")
  await settings.getByLabel("加入本班需要审批", { exact: true }).check()
  await settings.getByLabel("退出本班需要审批", { exact: true }).check()
  await settings.getByRole("button", { name: "保存班级设置", exact: true }).click()
  await expect(page.getByText("班级设置已保存", { exact: true })).toBeVisible()
  const members = section(page, "学生名单")
  await members.getByLabel(/^拉入已开通学生/).fill("b1_nonexistent_user")
  await members.getByRole("button", { name: "加入本班", exact: true }).click()
  await expect(page.getByRole("alert")).toContainText("学生账号不存在或无效")
  await members.getByLabel(/^拉入已开通学生/).fill("student")
  await members.getByRole("button", { name: "加入本班", exact: true }).click()
  await expect(members.getByText("student", { exact: true })).toBeVisible()
  await members.getByRole("button", { name: "移出本班", exact: true }).click()
  await expect(members.getByText("student", { exact: true })).toHaveCount(0)
  const invite = section(page, "班级邀请码")
  await invite.getByRole("button", { name: "生成新班级邀请码", exact: true }).click()
  await expect(invite.locator("code")).toBeVisible()
  const joinCode = (await invite.locator("code").textContent())!
  const logged = await request.post(api + "/api/v1/auth/login", { data: { school_code: "demo-a", username: "student", password: demo.password } })
  expect(logged.ok()).toBeTruthy()
  const token = (await logged.json()).access_token
  const joining = await request.post(api + "/api/v1/enrollments/join", { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": randomUUID() }, data: { invitation_code: joinCode } })
  expect(joining.status()).toBe(200)
  expect((await joining.json()).status).toBe("pending_join")
  await page.getByRole("button", { name: "刷新本班数据", exact: true }).click()
  await section(page, "加入与退出审批").getByRole("button", { name: "同意", exact: true }).click()
  await expect(members.getByText("student", { exact: true })).toBeVisible()
  const staff = section(page, "教师协作")
  await staff.getByLabel(/^查找本校教师/).fill("teacher_eng")
  await staff.getByRole("button", { name: "查找教师", exact: true }).click()
  await staff.getByLabel("选择教师", { exact: true }).selectOption({ label: "周老师（teacher_eng）" })
  await staff.getByRole("button", { name: "添加为协作教师", exact: true }).click()
  await expect(staff.getByRole("cell", { name: "周老师", exact: true })).toBeVisible()
  const other = await context.newPage()
  await signIn(other, "teacher_eng")
  const card = section(other, "有权访问的教学班").locator("article").filter({ has: other.getByRole("heading", { name: title, exact: true }) })
  await card.getByRole("button", { name: "管理教学班", exact: true }).click()
  await expect(other.getByRole("heading", { name: title, exact: true })).toBeVisible()
  await expect(other.getByRole("button", { name: "归档本教学班", exact: true })).toHaveCount(0)
  await expect(other.getByRole("button", { name: "转交为主教师", exact: true })).toHaveCount(0)
  await section(other, "学生名单").getByRole("button", { name: "移出本班", exact: true }).click()
  await expect(section(other, "学生名单").getByText("student", { exact: true })).toHaveCount(0)
  expect((await request.get(api + `/api/v1/courses/${course.id}`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(404)
  await staff.getByLabel("选择教师", { exact: true }).selectOption({ label: "周老师（teacher_eng）" })
  await staff.getByRole("button", { name: "转交为主教师", exact: true }).click()
  await staff.getByRole("button", { name: "确认转交主教师", exact: true }).click()
  await expect(page.getByRole("heading", { name: "我的课程与教学班", exact: true })).toBeVisible()
  await expect(section(page, "有权访问的教学班").getByRole("heading", { name: title, exact: true })).toHaveCount(0)
  await other.getByRole("button", { name: "刷新本班数据", exact: true }).click()
  await other.getByRole("button", { name: "归档本教学班", exact: true }).click()
  await other.getByRole("button", { name: "确认归档", exact: true }).click()
  await expect(other.getByText("已归档 · 历史只读", { exact: false })).toBeVisible()
  await other.close()
})

test("管理员邀请与 1440/390 布局、失败重试", async ({ page }) => {
  await signIn(page, "admin")
  await nav(page, "学生账号邀请")
  await section(page, "创建开通邀请").getByRole("button", { name: "生成学生账号邀请", exact: true }).click()
  await expect(page.getByText("本次生成的邀请码", { exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(import.meta.dirname, "../.artifacts/admin-1440.png"), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
  await page.screenshot({ path: path.join(import.meta.dirname, "../.artifacts/admin-390.png"), fullPage: true })
  await page.getByRole("button", { name: "撤销邀请", exact: true }).first().click()
  await expect(page.getByText("邀请已撤销", { exact: true })).toBeVisible()
  await page.route("**/api/v1/admin/accounts?**", route => route.abort("failed"))
  await nav(page, "账号与授权")
  await expect(section(page, "授权范围内的账号").getByRole("alert")).toContainText("无法连接服务")
  await page.unroute("**/api/v1/admin/accounts?**")
  await section(page, "授权范围内的账号").getByRole("button", { name: "重试", exact: true }).click()
  await expect(section(page, "授权范围内的账号").locator("table")).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
})

test("同一工作身份的搜索先后返回不会覆盖新结果", async ({ page }) => {
  await signIn(page, "admin")
  const accounts = section(page, "授权范围内的账号")
  await expect(accounts.locator("table")).toBeVisible()
  let release!: () => void
  let oldFetched = false
  let oldFinished = false
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route("**/api/v1/admin/accounts?**", async route => {
    if (new URL(route.request().url()).searchParams.get("q") !== "teacher") return route.continue()
    const response = await route.fetch()
    oldFetched = true
    await gate
    try { await route.fulfill({ response }) } finally { oldFinished = true }
  })
  try {
    await accounts.getByLabel("账号、姓名或学号", { exact: true }).fill("teacher")
    await accounts.getByRole("button", { name: "查询账号", exact: true }).click()
    await expect.poll(() => oldFetched).toBeTruthy()
    await accounts.getByLabel("账号、姓名或学号", { exact: true }).fill(unique("no_such_account"))
    await accounts.getByRole("button", { name: "查询账号", exact: true }).click()
    await expect(accounts.getByText("当前范围内没有匹配的账号。", { exact: true })).toBeVisible()
    release()
    await expect.poll(() => oldFinished).toBeTruthy()
    await expect(accounts.getByText("当前范围内没有匹配的账号。", { exact: true })).toBeVisible()
    await expect(accounts.locator("table")).toHaveCount(0)
  } finally { release() }
})
