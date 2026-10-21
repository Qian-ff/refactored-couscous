import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { reportDirectory, demoAccounts } from '../../others/scripts/web-environment.mjs'

const fixtures = demoAccounts()
const report = reportDirectory

async function login(page: Page, username: string) {
  await page.goto('/')
  await page.getByLabel('登录账号', { exact: true }).fill(username)
  await page.getByLabel('登录密码', { exact: true }).fill(fixtures.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: username === 'student' ? '我的课程' : username === 'teacher' ? '我的课程与教学班' : '课程与教学班管理', exact: true })).toBeVisible()
}

test('真实网页登录、写课程及另一账号同步读取', async ({ page, browser }) => {
  await page.goto('/')
  await page.screenshot({ path: path.join(report, 'web-login-desktop.png'), fullPage: true })
  await login(page, 'teacher')
  await page.getByRole('button', { name: '新建课程与首班', exact: true }).click()
  const code = `WEB-${Date.now()}`
  const title = `网页跨端验证 ${code}`
  await page.getByLabel('目录与首班代码', { exact: true }).fill(code)
  await page.getByLabel('课程与首班名称', { exact: true }).fill(title)
  await page.getByRole('button', { name: '确认创建教学班', exact: true }).click()
  await expect(page.getByText(`${title} 已建立。`, { exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(report, 'web-teacher-desktop.png'), fullPage: true })
  const adminContext = await browser.newContext()
  const admin = await adminContext.newPage()
  await login(admin, 'admin')
  await admin.getByLabel('名称或代码', { exact: true }).fill(code)
  await admin.getByRole('button', { name: '查询课程', exact: true }).click()
  await expect(admin.getByText(title, { exact: true }).first()).toBeVisible()
  await adminContext.close()
})

test('学生移动布局、课程权限与真实退出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'student')
  await expect(page.getByRole('heading', { name: '实验室通识安全', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建课程与首班' })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: path.join(report, 'web-student-mobile.png'), fullPage: true })
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('heading', { name: '欢迎使用安研通', exact: true })).toBeVisible()
})

test('错误密码与网络失败显示真实反馈', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('登录账号', { exact: true }).fill('teacher')
  await page.getByLabel('登录密码', { exact: true }).fill('wrong-password')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('学校、账号或密码不正确', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '连接设置', exact: true }).click()
  await page.getByLabel('服务地址', { exact: true }).fill('http://127.0.0.1:59999')
  await page.getByRole('button', { name: '保存连接设置', exact: true }).click()
  // A service change intentionally clears the old form and credentials.
  await page.getByLabel('登录账号', { exact: true }).fill('teacher')
  await page.getByLabel('登录密码', { exact: true }).fill(fixtures.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('无法连接服务，请检查服务地址和网络后重试', { exact: true })).toBeVisible()
})
