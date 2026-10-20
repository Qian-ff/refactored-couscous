import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'
import { webPort } from '../others/scripts/web-environment.mjs'

const edge = process.platform === 'win32' && existsSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 45_000, retries: 0,
  globalSetup: './tests/shared/global-setup.ts',
  outputDir: '../others/reports/a0/web-test-results',
  reporter: [['list'], ['json', { outputFile: '../others/reports/a0/web-tests.json' }]],
  use: { baseURL: `http://127.0.0.1:${webPort}`, channel: edge ? 'msedge' : undefined,
    viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure' },
  // A reachable port is only readiness; globalSetup verifies SHA, tree, content and contract before any test.
  webServer: { command: `node ../node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${webPort}`, url: `http://127.0.0.1:${webPort}`, reuseExistingServer: !process.env.CI, timeout: 60_000 },
})
