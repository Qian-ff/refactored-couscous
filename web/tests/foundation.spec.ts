import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { reportDirectory, demoAccounts } from '../../others/scripts/web-environment.mjs'

const fixtures = demoAccounts()
const report = reportDirectory

async function login(page: Page, username: string) {
  await page.goto('/')
  await page.getByLabel('账号', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(fixtures.password)
  await page.getByRole('button', { name: '登录学习空间' }).click()
  await expect(page.getByRole('heading', { name: '每一次实验，都从安全开始' })).toBeVisible()
}

test('真实网页登录、写课程及另一账号同步读取', async ({ page, browser }) => {
  await page.goto('/')
  await page.screenshot({ path: path.join(report, 'web-login-desktop.png'), fullPage: true })
  await login(page, 'teacher')
  await page.getByRole('button', { name: '新建课程' }).click()
  const code = `WEB-${Date.now()}`
  const title = `网页跨端验证 ${code}`
  await page.getByLabel('课程代码').fill(code)
  await page.getByLabel('课程名称').fill(title)
  await page.getByRole('button', { name: '保存课程', exact: true }).click()
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(report, 'web-teacher-desktop.png'), fullPage: true })
  const adminContext = await browser.newContext()
  const admin = await adminContext.newPage()
  await login(admin, 'admin')
  await expect(admin.getByRole('heading', { name: title, exact: true })).toBeVisible()
  await adminContext.close()
})

test('学生移动布局、课程权限与真实退出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'student')
  await expect(page.getByRole('heading', { name: '实验室通识安全', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建课程' })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: path.join(report, 'web-student-mobile.png'), fullPage: true })
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page.getByRole('heading', { name: '登录平台' })).toBeVisible()
})

test('错误密码与网络失败显示真实反馈', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('账号', { exact: true }).fill('teacher')
  await page.getByLabel('密码', { exact: true }).fill('wrong-password')
  await page.getByRole('button', { name: '登录学习空间' }).click()
  await expect(page.getByRole('alert')).toContainText('学校、账号或密码不正确')
  await page.getByRole('button', { name: '服务连接设置' }).click()
  await page.getByLabel('服务地址', { exact: true }).fill('http://127.0.0.1:59999')
  await page.getByRole('button', { name: '登录学习空间' }).click()
  await expect(page.getByRole('alert')).toContainText('无法连接服务')
})
