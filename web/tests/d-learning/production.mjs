// Verify the actual production output, with no default debug API and no design-directory dependency.
import { chromium, expect } from "@playwright/test"
import { createServer } from "node:http"
import fs from "node:fs"
import path from "node:path"
import { reportDirectory, root, sourceIdentity, webPort } from "../../../others/scripts/web-environment.mjs"

const dist = path.join(root, "web/dist")
const info = JSON.parse(fs.readFileSync(path.join(dist, "build-info.json"), "utf8"))
const source = sourceIdentity("web")
for (const field of ["source_sha", "source_fingerprint", "contract"]) {
  if (info[field] !== source[field]) throw new Error("Production artifact is stale: " + field)
}
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".ttf": "font/ttf", ".txt": "text/plain", ".json": "application/json" }
const server = createServer((req, res) => {
  const relative = decodeURIComponent(new URL(req.url, "http://localhost").pathname)
  const file = path.resolve(dist, relative === "/" ? "index.html" : "." + relative)
  if (!file.startsWith(dist + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return }
  res.setHeader("Content-Type", types[path.extname(file)] || "application/octet-stream")
  fs.createReadStream(file).pipe(res)
})
await new Promise((resolve, reject) => { server.once("error", reject); server.listen(webPort, "127.0.0.1", resolve) })
let browser
try {
  browser = await chromium.launch({ channel: "msedge" })
  const page = await browser.newPage()
  const external = []
  const apiCalls = [], fontRequests = []
  page.on("request", request => {
    if (!request.url().startsWith(`http://127.0.0.1:${webPort}/`) && !request.url().startsWith("data:")) external.push(new URL(request.url()).origin)
    if (request.url().includes("/api/v1/")) apiCalls.push(new URL(request.url()).pathname)
    if (request.url().endsWith(".ttf")) fontRequests.push(new URL(request.url()).pathname)
  })
  await page.goto(`http://127.0.0.1:${webPort}/`)
  await expect(page.getByRole("heading", { name: "尚未配置服务" })).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  const license = await page.getByRole("link", { name: "字体许可", exact: true }).getAttribute("href")
  const licenseResponse = await page.request.get(new URL(license, page.url()).href)
  expect(licenseResponse.status()).toBe(200)
  expect(await licenseResponse.text()).toContain("SIL OPEN FONT LICENSE")
  await page.getByRole("button", { name: "连接设置", exact: true }).click()
  await page.getByLabel("服务地址", { exact: true }).fill("http://127.0.0.1:8000")
  await page.getByRole("button", { name: "保存连接设置", exact: true }).click()
  await expect(page.getByRole("alert")).toContainText("HTTPS")
  await page.keyboard.press("Escape")
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
    await expect(page.getByRole("heading", { name: "尚未配置服务" })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy()
    await page.screenshot({ path: path.join(reportDirectory, `production-unconfigured-${width}.png`), fullPage: true })
  }
  expect(external).toEqual([])
  expect(apiCalls).toEqual([])
  expect(fontRequests.length).toBeGreaterThan(0)
  fs.mkdirSync(reportDirectory, { recursive: true })
  fs.writeFileSync(path.join(reportDirectory, "production.json"), JSON.stringify({ build: info, source, fontLicenseBundled: true, unconfigured: true, insecureServiceRejected: true, externalRequests: external, unconfiguredApiRequests: apiCalls, packagedFontRequests: fontRequests, viewports: [1440, 390] }, null, 2))
  process.stdout.write("Production artifact: source, packaged font/license, unconfigured state, HTTPS policy and layouts passed.\n")
} finally {
  await browser?.close()
  await new Promise(resolve => server.close(resolve))
}
