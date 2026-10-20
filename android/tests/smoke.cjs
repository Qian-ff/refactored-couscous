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
  function nativeWindow() {
    command('shell', 'uiautomator', 'dump', '/sdcard/labconnect-window.xml')
    const xml = command('shell', 'cat', '/sdcard/labconnect-window.xml')
    if (xml.includes('android:id/aerr_') || !xml.includes('package="' + pkg + '"')) {
      throw new Error('Native Android UI is obstructed or the app is not in the foreground')
    }
    return xml
  }
  try {
    const devices = await _android.devices({ omitDriverInstall: true })
    device = devices.find(candidate => candidate.serial() === serial)
    if (!device) throw new Error('Selected emulator is not visible to Playwright')
    device.setDefaultTimeout(30_000)
    const view = await device.webView({ pkg }, { timeout: 60_000 })
    const page = await view.page()
    page.setDefaultTimeout(30_000)
    await expect(page).toHaveTitle('安研通')
    // A first boot may expose ADB before the guest network is ready.
    await expect.poll(() => page.evaluate(async () => {
      try { return (await fetch('http://10.0.2.2:8000/api/v1/health', { signal: AbortSignal.timeout(3000) })).status }
      catch { return 0 }
    }), { timeout: 45_000, message: 'Android guest network must reach the real backend' }).toBe(200)
    await page.screenshot({ path: path.join(reports, 'android-login.png') })
    async function login(target, username) {
      await target.getByLabel('账号', { exact: true }).fill(username)
      await target.getByLabel('密码', { exact: true }).fill(fixtures.password)
      await target.getByRole('button', { name: '登录学习空间' }).click()
      await expect(target.getByRole('heading', { name: '每一次实验，都从安全开始' })).toBeVisible({ timeout: 30_000 })
    }
    await login(page, 'teacher')
    const windows = JSON.parse(fs.readFileSync(path.join(reports, 'windows-test.json'), 'utf8'))
    await expect(page.getByRole('heading', { name: windows.courseTitle, exact: true })).toBeVisible()
    const code = 'AND-' + Date.now()
    const title = '安卓跨端验证 ' + code
    await page.getByRole('button', { name: '新建课程' }).click()
    await page.getByLabel('课程代码').fill(code)
    await page.getByLabel('课程名称').fill(title)
    await page.getByRole('button', { name: '保存课程', exact: true }).click()
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(reports, 'android-teacher.png') })
    const edge = fs.existsSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    browser = await chromium.launch({ channel: edge ? 'msedge' : undefined, headless: true })
    const web = await browser.newPage()
    await web.goto('http://127.0.0.1:5173')
    await login(web, 'admin')
    await expect(web.getByRole('heading', { name: title, exact: true })).toBeVisible()
    const webCode = 'WEB-ANDROID-' + Date.now()
    const webTitle = '网页到安卓验证 ' + webCode
    await web.getByRole('button', { name: '新建课程' }).click()
    await web.getByLabel('所属学院').selectOption(fixtures.ids.colleges['a-chem'])
    await web.getByLabel('主教师').selectOption(fixtures.ids.users.teacher)
    await web.getByLabel('课程代码').fill(webCode)
    await web.getByLabel('课程名称').fill(webTitle)
    await web.getByRole('button', { name: '保存课程', exact: true }).click()
    await expect(web.getByRole('heading', { name: webTitle, exact: true })).toBeVisible()
    await page.getByRole('button', { name: '刷新课程' }).click()
    await expect(page.getByRole('heading', { name: webTitle, exact: true })).toBeVisible()
    // Exercise a real Android touch, using observed DOM and native WebView bounds.
    const logout = page.getByRole('button', { name: '退出登录' })
    await logout.scrollIntoViewIfNeeded()
    const rect = await logout.boundingBox()
    const xml = nativeWindow()
    const bounds = xml.match(/resource-id="cn\.labconnect\.platform:id\/webview"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/)
    if (!rect || !bounds) throw new Error('Cannot locate native WebView/touch target')
    const ratio = await page.evaluate(() => window.devicePixelRatio)
    command('shell', 'input', 'tap', String(Math.round(Number(bounds[1]) + (rect.x + rect.width / 2) * ratio)),
      String(Math.round(Number(bounds[2]) + (rect.y + rect.height / 2) * ratio)))
    await expect(page.getByRole('heading', { name: '登录平台' })).toBeVisible()
    await login(page, 'student')
    await expect(page.getByRole('heading', { name: '实验室通识安全', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建课程' })).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: path.join(reports, 'android-student.png'), fullPage: true })
    nativeWindow()
    await device.screenshot({ path: path.join(reports, 'android-device.png') })
    fs.writeFileSync(path.join(reports, 'android-test.json'), JSON.stringify({ result: 'passed', serial,
      model: device.model(), api: command('shell', 'getprop', 'ro.build.version.sdk'),
      abi: command('shell', 'getprop', 'ro.product.cpu.abi'), imageRevision: 7, package: pkg,
      apk: path.relative(root, apk), installed: true, launched: true, createdInAndroid: code,
      visibleInWeb: true, createdInWeb: webCode, visibleInAndroid: true, windowsCourseVisibleInAndroid: windows.courseCode,
      logoutAndStudentScope: true, nativeTouchLogout: true, nativeUiUnobstructed: true, physicalDeviceTested: false }, null, 2))
    console.log('PASS: real APK installed/launched; Android and web exchange real courses; student scope and logout verified')
  } finally {
    await browser?.close()
    await device?.close()
  }
}
main().catch(error => { console.error(error.stack || error.message); process.exitCode = 1 })
