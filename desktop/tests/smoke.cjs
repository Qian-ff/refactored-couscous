const { _electron, chromium, expect } = require('@playwright/test')
const fs = require('node:fs')
const path = require('node:path')

async function main() {
  const root = path.resolve(__dirname, '../..')
  const health = await fetch('http://127.0.0.1:8000/api/v1/health', { signal: AbortSignal.timeout(10_000) })
  if (!health.ok) throw new Error('Backend/DB not ready: HTTP ' + health.status)
  const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'others/runtime/demo-accounts.json'), 'utf8'))
  const report = path.join(root, 'others/reports/a1')
  const portable = path.join(root, 'others/runtime', 'portable-test-' + Date.now())
  fs.cpSync(path.join(root, 'desktop/release/win-unpacked'), portable, { recursive: true })
  fs.mkdirSync(report, { recursive: true })
  const env = { ...process.env, SAFELAB_TEST_HEADLESS: '0' }
  delete env.ELECTRON_RUN_AS_NODE
  let application, browser
  try {
    application = await _electron.launch({ executablePath: path.join(portable, 'LabConnect.exe'), cwd: portable, env, timeout: 60_000 })
    const page = await application.firstWindow()
    await expect(page).toHaveTitle('安研通')
    async function login(target, username) {
      await target.getByLabel('账号', { exact: true }).fill(username)
      await target.getByLabel('密码', { exact: true }).fill(fixtures.password)
      await target.getByRole('button', { name: '登录学习空间' }).click()
      await expect(target.getByRole('heading', { name: '每一次实验，都从安全开始' })).toBeVisible({ timeout: 20_000 })
    }
    await login(page, 'teacher')
    const code = 'WIN-' + Date.now()
    const title = 'Windows 跨端验证 ' + code
    await page.getByRole('button', { name: '新建课程' }).click()
    await page.getByLabel('课程代码').fill(code)
    await page.getByLabel('课程名称').fill(title)
    await page.getByRole('button', { name: '保存课程', exact: true }).click()
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(report, 'windows-packaged.png'), fullPage: true })
    expect(await page.evaluate(() => typeof window.require)).toBe('undefined')
    const edge = fs.existsSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    browser = await chromium.launch({ channel: edge ? 'msedge' : undefined, headless: true })
    const web = await browser.newPage()
    await web.goto('http://127.0.0.1:48621')
    await login(web, 'admin')
    await expect(web.getByRole('heading', { name: title, exact: true })).toBeVisible()
    const details = await application.evaluate(({ app }) => ({ packaged: app.isPackaged, version: app.getVersion(), electron: process.versions.electron }))
    expect(details.packaged).toBe(true)
    fs.writeFileSync(path.join(report, 'windows-test.json'), JSON.stringify({ ...details, result: 'passed',
      portableDirectory: path.relative(root, portable), cwd: 'portable directory', rendererNodeIntegration: false,
      courseCode: code, courseTitle: title, createdInWindows: true, visibleInWeb: true }, null, 2))
    console.log('PASS: packaged Windows client launches outside source tree, logs in, writes course; browser sees it')
  } finally { await browser?.close(); await application?.close() }
}
main().catch(error => { console.error(error.message); process.exitCode = 1 })
