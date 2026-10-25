import shared from "../../playwright.config"
import { defineConfig } from "@playwright/test"
import { fileURLToPath } from "node:url"

const server = shared.webServer
if (!server || Array.isArray(server)) throw new Error("Component suite expects one project web server")
// Component-only fixture suite: its beforeAll verifies D web; no material API exists yet.
export default defineConfig({ ...shared, testDir: ".", testMatch: ["content-components.spec.ts", "material-adapter.spec.ts"], globalSetup: undefined,
  use: { ...shared.use, trace: "off" },
  webServer: { ...server, cwd: fileURLToPath(new URL("../../", import.meta.url)) },
})
