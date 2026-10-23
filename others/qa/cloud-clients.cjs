// Read-only existing UI acceptance against the cloud; credentials/screenshots remain ignored.
const fs = require('node:fs/promises'), path = require('node:path'), cp = require('node:child_process')
const { createRequire } = require('node:module')
const { chromium, _electron, _android, expect } = createRequire(path.join(process.cwd(), 'web/package.json'))('@playwright/test')
const root = process.cwd(), report = path.join(root, 'others/reports/cloud-asr')
const command = (...args) => cp.execFileSync('D:/AndroidSDK/platform-tools/adb.exe', ['-s', 'emulator-5556', ...args], { encoding: 'utf8', timeout: 30000 })
let stage = 'setup', app, device, browser
const checks = []
async function main() {
  const state = JSON.parse(await fs.readFile(path.join(root, 'others/runtime/cloud-ecs/secrets/accounts.json'), 'utf8'))
  const cloud = state.service_url
  const info = await (await fetch(cloud + '/build-info.json')).json()
  const nativeSha = cp.execFileSync('git', ['rev-parse', 'existing-ui-accepted^{}'], { encoding: 'utf8' }).trim()
  await fs.mkdir(report, { recursive: true })
  async function exercise(page, surface, native) {
    const actual = await page.evaluate(async () => (await fetch('/build-info.json')).json())
    if (native) {
      expect(actual.source_sha).toMatch(/^[0-9a-f]{40}$/)
      cp.execFileSync('git', ['merge-base', '--is-ancestor', nativeSha, actual.source_sha])
      cp.execFileSync('git', ['merge-base', '--is-ancestor', actual.source_sha, 'HEAD'])
    } else expect(actual.source_sha).toBe(info.source_sha)
    expect(actual.source_fingerprint).toBe(info.source_fingerprint)
    expect(actual.contract).toBe('0.3.2')
    const original = await page.evaluate(() => localStorage.getItem('safelab.service'))
    const origins = new Set(), errors = []
    page.on('request', r => { const url = new URL(r.url()); if (url.pathname.startsWith('/api/v1/')) origins.add(url.origin) })
    page.on('pageerror', () => errors.push('pageerror'))
    try {
      for (const role of ['teacher', 'admin', 'student']) {
        stage = surface + ':' + role
        // Enter the public login route explicitly; a previous role's deep link remains permission-guarded.
        await page.evaluate(() => { location.hash = '/login' })
        if (native) {
          await page.getByRole('button', { name: '连接设置', exact: true }).click()
          await page.getByLabel('服务地址', { exact: true }).fill(cloud)
          await page.getByRole('button', { name: '保存连接设置', exact: true }).click()
        }
        const account = state.demo_accounts[role]
        await page.getByLabel('学校代码', { exact: true }).fill(account.school_code)
        await page.getByLabel('登录账号', { exact: true }).fill(account.username)
        await page.getByLabel('登录密码', { exact: true }).fill(account.password)
        const confirmed = page.waitForResponse(r => r.url() === cloud + '/api/v1/auth/me' && r.request().method() === 'GET')
        await page.getByRole('button', { name: '登录', exact: true }).click()
        const response = await confirmed, me = await response.json()
        expect(response.status()).toBe(200)
        expect(me.active_work_role).toBe(role === 'admin' ? 'administrator' : role)
        const heading = role === 'teacher' ? '我的课程与教学班' : role === 'admin' ? '课程与教学班管理' : '我的课程'
        stage = surface + ':' + role + ':heading'
        await expect(page.getByRole('heading', { level: 1, name: heading, exact: true })).toBeVisible({ timeout: 20000 })
        stage = surface + ':' + role + ':course'
        await expect(page.getByText('云端合成演示：实验室安全', { exact: true }).first()).toBeVisible()
        if (surface.startsWith('web-')) await page.screenshot({ path: path.join(report, surface + '-' + role + '.png'), fullPage: true })
        if (surface === 'android-emulator') {
          const target = '/sdcard/labconnect-cloud-asr.xml'
          command('shell', 'uiautomator', 'dump', target)
          const xml = command('shell', 'cat', target)
          expect(xml.includes('package="cn.labconnect.platform"') && !xml.includes('android:id/aerr_')).toBeTruthy()
          await device.screenshot({ path: path.join(report, surface + '-' + role + '.png') })
        }
        const logout = page.waitForResponse(r => r.url() === cloud + '/api/v1/auth/logout')
        await page.getByRole('button', { name: '退出登录', exact: true }).click()
        expect((await logout).status()).toBe(200)
        await expect(page.getByRole('heading', { name: '欢迎使用安研通', exact: true })).toBeVisible()
        expect([...origins]).toEqual([cloud]); expect(errors).toEqual([])
        checks.push({ surface, role, status: 'passed', client_source_sha: actual.source_sha,
          api_deployment_sha: info.source_sha, contract: actual.contract, actual_api_origins: [...origins] })
        console.log(JSON.stringify({ surface, role, status: 'passed' }))
      }
    } catch (error) {
      await fs.writeFile(path.join(report, 'client-failure-dom.json'), JSON.stringify(await page.evaluate(() => ({
        hash: location.hash, headings: [...document.querySelectorAll('h1,h2')].map(v => v.textContent),
        main_text: document.querySelector('main')?.textContent, alerts: [...document.querySelectorAll('[role="alert"]')].map(v => v.textContent),
      })), null, 2) + '\n')
      throw error
    } finally {
      if (native) {
        await page.evaluate(value => { if (value === null) localStorage.removeItem('safelab.service'); else localStorage.setItem('safelab.service', value) }, original)
        await page.reload()
      }
    }
  }
  browser = await chromium.launch({ channel: 'msedge', headless: true })
  for (const [surface, viewport] of [['web-desktop', { width: 1440, height: 960 }], ['web-mobile', { width: 390, height: 844 }]]) {
    const context = await browser.newContext({ viewport })
    try { const page = await context.newPage(); await page.goto(cloud); await exercise(page, surface, false) }
    finally { await context.close() }
  }
  await browser.close(); browser = null
  const env = { ...process.env, SAFELAB_TEST_HEADLESS: '1' }; delete env.ELECTRON_RUN_AS_NODE
  app = await _electron.launch({ executablePath: path.join(root, 'desktop/release/win-unpacked/LabConnect.exe'),
    args: ['--user-data-dir=' + path.join(root, 'others/runtime/cloud-asr/windows-' + Date.now())], env, cwd: root, timeout: 60000 })
  await exercise(await app.firstWindow(), 'windows-package', true)
  await app.close(); app = null
  stage = 'android-connect'
  command('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'); command('shell', 'wm', 'dismiss-keyguard')
  command('shell', 'am', 'force-stop', 'cn.labconnect.platform')
  command('shell', 'am', 'start', '-n', 'cn.labconnect.platform/.MainActivity')
  device = (await _android.devices({ omitDriverInstall: true })).find(value => value.serial() === 'emulator-5556')
  if (!device) throw new Error('Project emulator missing')
  const page = await (await device.webView({ pkg: 'cn.labconnect.platform' }, { timeout: 60000 })).page()
  await exercise(page, 'android-emulator', true)
  await fs.writeFile(path.join(report, 'clients.json'), JSON.stringify({ status: 'passed', checks,
    windows_hidden_dom_verified: true, physical_android_tested: false, packages_rebuilt_this_round: false }, null, 2) + '\n')
}
main().catch(async error => {
  const value = { status: 'failed', stage, type: error.name, checks }
  await fs.mkdir(report, { recursive: true }); await fs.writeFile(path.join(report, 'clients.json'), JSON.stringify(value, null, 2) + '\n')
  // Avoid error/call-log serialization: a failed form fill may contain a password.
  console.error(JSON.stringify(value)); process.exitCode = 1
}).finally(async () => { await app?.close(); await device?.close(); await browser?.close() })
