import path from "node:path"
import { existsSync } from "node:fs"
import { defineConfig } from "@playwright/test"
import { root, webPort } from "../../../../../others/scripts/web-environment.mjs"

process.env.LABCONNECT_API_ROOT ||= root
process.env.LABCONNECT_API_URL ||= "http://127.0.0.1:8001"
export default defineConfig({
  testDir: "./tests", workers: 1, timeout: 60_000, retries: 0,
  globalSetup: "./verify-services.ts", outputDir: "./.artifacts/test-results",
  reporter: [["list"], ["json", { outputFile: path.join(import.meta.dirname, ".artifacts/results.json") }]],
  use: { baseURL: `http://127.0.0.1:${webPort}`, viewport: { width: 1440, height: 1000 },
    channel: process.platform === "win32" && existsSync("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") ? "msedge" : undefined,
    trace: "retain-on-failure" },
  webServer: { command: `node ../node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${webPort}`,
    cwd: path.join(root, "web"), url: `http://127.0.0.1:${webPort}`, reuseExistingServer: true, timeout: 60_000 },
})
