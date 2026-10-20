import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'

const edge = process.platform === 'win32' && existsSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 45_000, retries: 0,
  outputDir: '../others/reports/a1/web-test-results',
  reporter: [['list'], ['json', { outputFile: '../others/reports/a1/web-tests.json' }]],
  use: { baseURL: 'http://127.0.0.1:5173', channel: edge ? 'msedge' : undefined,
    viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure' },
  webServer: { command: 'node ../node_modules/vite/bin/vite.js --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI, timeout: 60_000 },
})
