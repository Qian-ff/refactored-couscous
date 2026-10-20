// Real debug APK/WebView test against the shared PostgreSQL-backed service.
const { _android, chromium, expect } = require('@playwright/test')
const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

async function main() {
  const root = path.resolve(__dirname, '../..')
  const local = JSON.parse(fs.readFileSync(path.join(root, 'others/config/local.json'), 'utf8'))
  const adb = path.join(process.env.ANDROID_SDK_ROOT || local.android_sdk_root, 'platform-tools/adb.exe')
  const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'others/runtime/demo-accounts.json'), 'utf8'))
  const reports = path.join(root, 'others/reports/a1')
  fs.mkdirSync(reports, { recursive: true })
  const serial = process.env.ANDROID_SERIAL || 'emulator-5556'
  const pkg = 'cn.labconnect.platform'
  const command = (...args) => execFileSync(adb, ['-s', serial, ...args], { encoding: 'utf8', timeout: 120_000 }).trim()
  const health = await fetch('http://127.0.0.1:8000/api/v1/health', { signal: AbortSignal.timeout(10_000) })
  if (!health.ok) throw new Error('Backend/DB not ready: HTTP ' + health.status)
  if (command('shell', 'getprop', 'sys.boot_completed') !== '1') throw new Error('Start SafeLab_API36 and wait for boot completion')
  const apk = path.join(root, 'android/native/app/build/outputs/apk/debug/app-debug.apk')
  const installed = command('install', '-r', apk)
  if (!installed.includes('Success')) throw new Error('APK installation failed: ' + installed)
  command('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
  command('shell', 'wm', 'dismiss-keyguard')
  command('shell', 'am', 'force-stop', pkg)
  command('shell', 'am', 'start', '-n', pkg + '/.MainActivity')
  let device, browser
  try {
    const devices = await _android.devices({ omitDriverInstall: true })
    device = devices.find(candidate => candidate.serial() === serial)
    if (!device) throw new Error('Selected emulator is not visible to Playwright')
    device.setDefaultTimeout(30_000)
    const view = await device.webView({ pkg }, { timeout: 60_000 })
    const page = await view.page()
    await expect(page).toHaveTitle('安研通')
    await page.screenshot({ path: path.join(reports, 'android-login.png') })
    async function login(target, username) {
      await target.getByLabel('账号', { exact: true }).fill(username)
      await target.getByLabel('密码', { exact: true }).fill(fixtures.password)
      await target.getByRole('button', { name: '登录学习空间' }).click()
      await expect(target.getByRole('heading', { name: '每一次实验，都从安全开始' })).toBeVisible({ timeout: 30_000 })
    }
    await login(page, 'teacher')
    const code = 'AND-' + Date.now()
    const title = '安卓跨端验证 ' + code
    await page.getByRole('button', { name: '新建课程' }).click()
    await page.getByLabel('课程代码').fill(code)
    await page.getByLabel('课程名称').fill(title)
    await page.getByRole('button', { name: '保存课程', exact: true }).click()
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(reports, 'android-teacher.png'), fullPage: true })
    const edge = fs.existsSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    browser = await chromium.launch({ channel: edge ? 'msedge' : undefined, headless: true })
    const web = await browser.newPage()
    await web.goto('http://127.0.0.1:5173')
    await login(web, 'admin')
    await expect(web.getByRole('heading', { name: title, exact: true })).toBeVisible()
    const webCode = 'WEB-ANDROID-' + Date.now()
    const webTitle = '网页到安卓验证 ' + webCode
    await web.getByRole('button', { name: '新建课程' }).click()
    await web.getByLabel('课程代码').fill(webCode)
    await web.getByLabel('课程名称').fill(webTitle)
    await web.getByRole('button', { name: '保存课程', exact: true }).click()
    await expect(web.getByRole('heading', { name: webTitle, exact: true })).toBeVisible()
    await page.getByRole('button', { name: '刷新课程' }).click()
    await expect(page.getByRole('heading', { name: webTitle, exact: true })).toBeVisible()
    await page.getByRole('button', { name: '退出登录' }).click()
    await expect(page.getByRole('heading', { name: '登录平台' })).toBeVisible()
    await login(page, 'student')
    await expect(page.getByRole('heading', { name: '实验室通识安全', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建课程' })).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: path.join(reports, 'android-student.png'), fullPage: true })
    await device.screenshot({ path: path.join(reports, 'android-device.png') })
    fs.writeFileSync(path.join(reports, 'android-test.json'), JSON.stringify({ result: 'passed', serial,
      model: device.model(), api: command('shell', 'getprop', 'ro.build.version.sdk'),
      abi: command('shell', 'getprop', 'ro.product.cpu.abi'), imageRevision: 7, package: pkg,
      apk: path.relative(root, apk), installed: true, launched: true, createdInAndroid: code,
      visibleInWeb: true, createdInWeb: webCode, visibleInAndroid: true,
      logoutAndStudentScope: true, physicalDeviceTested: false }, null, 2))
    console.log('PASS: real APK installed/launched; Android and web exchange real courses; student scope and logout verified')
  } finally {
    await browser?.close()
    await device?.close()
  }
}
main().catch(error => { console.error(error.stack || error.message); process.exitCode = 1 })
