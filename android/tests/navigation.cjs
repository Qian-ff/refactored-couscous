// Real Android system Back regression. Requires the project emulator, A8000 and a fresh debug APK.
const { _android, expect } = require('@playwright/test')
const { execFileSync } = require('node:child_process')
const fs = require('node:fs'), path = require('node:path')
const { createHash } = require('node:crypto')

async function main() {
  const root = path.resolve(__dirname, '../..'), serial = process.env.ANDROID_SERIAL || 'emulator-5556'
  const local = JSON.parse(fs.readFileSync(path.join(root, 'others/config/local.json'), 'utf8'))
  const adb = path.join(process.env.ANDROID_SDK_ROOT || local.android_sdk_root, 'platform-tools/adb.exe')
  const command = (...args) => execFileSync(adb, ['-s', serial, ...args], { encoding: 'utf8', timeout: 30000 })
  const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'others/runtime/demo-accounts.json'), 'utf8'))
  const report = path.join(root, 'others/reports/android-navigation')
  fs.mkdirSync(report, { recursive: true })
  const pkg = 'cn.labconnect.platform', base = 'http://10.0.2.2:8000'
  const expected = JSON.parse(execFileSync('python', [path.join(root, 'others/scripts/provenance.py'), '--surface', 'web'], { encoding: 'utf8' }))
  command('install', '-r', path.join(root, 'android/native/app/build/outputs/apk/debug/app-debug.apk'))
  command('shell', 'am', 'force-stop', pkg)
  command('shell', 'am', 'start', '-n', pkg + '/.MainActivity')
  const device = (await _android.devices({ omitDriverInstall: true })).find(item => item.serial() === serial)
  if (!device) throw new Error('Selected project device unavailable')
  let page, originalService, release, blocked, stage = 'setup'
  const imeSetting = command('shell', 'settings', 'get', 'secure', 'show_ime_with_hard_keyboard').trim()
  if (serial.startsWith('emulator-')) command('shell', 'settings', 'put', 'secure', 'show_ime_with_hard_keyboard', '1')
  const checks = []
  function back() { command('shell', 'input', 'keyevent', 'KEYCODE_BACK') }
  function hideKeyboard() {
    if (/mInputShown=true/.test(command('shell', 'dumpsys', 'input_method'))) back()
  }
  function foreground() {
    const window = command('shell', 'dumpsys', 'window')
    if (!window.split('\n').some(line => line.includes('mCurrentFocus=') && line.includes(pkg))) throw new Error('App left foreground')
  }
  try {
    page = await (await device.webView({ pkg }, { timeout: 60000 })).page()
    page.setDefaultTimeout(15000)
    const info = await page.evaluate(async () => (await fetch('/build-info.json')).json())
    expect(info).toEqual(Object.fromEntries(['source_sha', 'source_fingerprint', 'contract'].map(key => [key, expected[key]])))
    originalService = await page.evaluate(() => localStorage.getItem('safelab.service'))
    await page.getByRole('button', { name: '连接设置', exact: true }).click()
    await page.getByLabel('服务地址', { exact: true }).fill(base)
    await page.getByRole('button', { name: '保存连接设置', exact: true }).click()
    await page.getByLabel('学校代码', { exact: true }).fill('demo-a')
    await page.getByLabel('登录账号', { exact: true }).fill('student')
    await page.getByLabel('登录密码', { exact: true }).fill(fixtures.password)
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: '我的课程', exact: true })).toBeVisible()
    stage = 'idle-dialog'
    await page.getByRole('button', { name: '使用班级邀请码加入', exact: true }).click()
    const input = page.getByLabel('班级邀请码', { exact: true })
    await input.scrollIntoViewIfNeeded()
    const filename = '/sdcard/labconnect-nav-keyboard-' + Date.now() + '.xml'
    command('shell', 'uiautomator', 'dump', filename)
    const xml = command('shell', 'cat', filename)
    const bounds = xml.match(/class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/)
    const box = await input.boundingBox(), ratio = await page.evaluate(() => devicePixelRatio)
    if (!bounds || !box) throw new Error('Native input touch bounds unavailable')
    command('shell', 'input', 'tap', String(Math.round(Number(bounds[1]) + (box.x + box.width / 2) * ratio)), String(Math.round(Number(bounds[2]) + (box.y + box.height / 2) * ratio)))
    await expect.poll(() => /mInputShown=true/.test(command('shell', 'dumpsys', 'input_method'))).toBe(true)
    const submit = page.getByRole('button', { name: '确认加入教学班', exact: true })
    await submit.scrollIntoViewIfNeeded()
    const actionBox = await submit.boundingBox(), viewport = await page.evaluate(() => ({ height: visualViewport.height, top: visualViewport.offsetTop }))
    expect(actionBox.y).toBeGreaterThanOrEqual(viewport.top - 1)
    expect(actionBox.y + actionBox.height).toBeLessThanOrEqual(viewport.top + viewport.height + 1)
    await device.screenshot({ path: path.join(report, 'native-keyboard-empty-dialog.png') })
    hideKeyboard()
    await expect(page.getByRole('dialog')).toBeVisible()
    checks.push('native-keyboard-visible-action-reachable-and-back-dismisses-keyboard-first')
    back()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    foreground(); checks.push('idle-dialog-closes-without-navigation')
    stage = 'busy-dialog'
    const entered = new Promise(resolve => { blocked = resolve })
    await page.route('**/api/v1/enrollments/join', async route => {
      await new Promise(resolve => { release = resolve; blocked() })
      await route.continue()
    })
    await page.getByRole('button', { name: '使用班级邀请码加入', exact: true }).click()
    await page.getByLabel('班级邀请码', { exact: true }).fill('NativeNavigationDeliberatelyInvalidCode')
    await page.getByRole('button', { name: '确认加入教学班', exact: true }).click()
    await entered
    hideKeyboard(); back()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByRole('button', { name: '关闭使用班级邀请码加入', exact: true })).toBeDisabled()
    foreground(); checks.push('pending-write-dialog-stays-open')
    const response = page.waitForResponse(value => value.url().endsWith('/api/v1/enrollments/join'))
    release(); release = undefined
    expect((await response).status()).not.toBe(200)
    await expect(page.getByRole('button', { name: '关闭使用班级邀请码加入', exact: true })).toBeEnabled()
    hideKeyboard(); back()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await page.unroute('**/api/v1/enrollments/join')
    stage = 'class-history'
    await page.getByLabel('搜索课程', { exact: true }).fill('GENERAL')
    await page.locator('form').filter({ has: page.getByLabel('搜索课程', { exact: true }) }).getByRole('button', { name: '搜索', exact: true }).click()
    await expect(page.locator('.lc-course-card')).toHaveCount(1)
    await page.getByRole('link', { name: '查看班级', exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: '实验室通识安全', exact: true })).toBeVisible()
    hideKeyboard(); back()
    await expect(page.getByRole('heading', { level: 1, name: '我的课程', exact: true })).toBeVisible()
    foreground(); checks.push('class-detail-returns-to-course-list')
    stage = 'logout-history'
    await page.getByRole('button', { name: '退出登录', exact: true }).click()
    await expect(page.getByRole('heading', { name: '欢迎使用安研通', exact: true })).toBeVisible()
    back()
    if (!page.isClosed()) {
      await expect(page.getByRole('heading', { name: '欢迎使用安研通', exact: true })).toBeVisible()
      await expect(page.locator('.lc-course-card')).toHaveCount(0)
    }
    checks.push('logout-back-never-restores-private-content')
    fs.writeFileSync(path.join(report, 'result.json'), JSON.stringify({ status: 'passed', source: info, checks,
      android_activity_sha256: createHash('sha256').update(fs.readFileSync(path.join(root, 'android/native/app/src/main/java/cn/labconnect/platform/MainActivity.java'))).digest('hex'),
      device: serial, physical_device: !serial.startsWith('emulator-'), no_business_success_mocked: true }, null, 2) + '\n')
    console.log(JSON.stringify({ status: 'passed', checks }))
  } catch (error) {
    fs.writeFileSync(path.join(report, 'result.json'), JSON.stringify({ status: 'failed', stage, checks,
      first_line: String(error.message).split('\n')[0] }, null, 2) + '\n')
    throw error
  } finally {
    release?.()
    if (serial.startsWith('emulator-')) {
      if (imeSetting === 'null') command('shell', 'settings', 'delete', 'secure', 'show_ime_with_hard_keyboard')
      else command('shell', 'settings', 'put', 'secure', 'show_ime_with_hard_keyboard', imeSetting)
    }
    if (page && !page.isClosed() && originalService !== undefined) await page.evaluate(value => {
      if (value === null) localStorage.removeItem('safelab.service'); else localStorage.setItem('safelab.service', value)
    }, originalService).catch(() => {})
    await device.close()
  }
}
main().catch(error => { console.error(String(error.message).split('\n')[0]); process.exitCode = 1 })
