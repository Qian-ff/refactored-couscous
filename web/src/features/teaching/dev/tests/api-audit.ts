import fs from "node:fs"
import path from "node:path"
import { createHash } from "node:crypto"
import { expect, test, type BrowserContext } from "@playwright/test"
import { root } from "../../../../../../others/scripts/web-environment.mjs"

/** Record URL metadata only; never store auth headers, request bodies or query values. */
export function auditApiOrigins() {
  const audits = new WeakMap<BrowserContext, { origins: Set<string>; requests: number }>()
  const expected = new URL(process.env.LABCONNECT_API_URL || "http://127.0.0.1:8001").origin
  test.beforeEach(async ({ context }) => {
    const audit = { origins: new Set<string>(), requests: 0 }
    audits.set(context, audit)
    context.on("request", request => {
      const url = new URL(request.url())
      if (url.pathname.startsWith("/api/v1/")) { audit.origins.add(url.origin); audit.requests++ }
    })
  })
  test.afterEach(async ({ context }, info) => {
    const audit = audits.get(context)!
    const key = createHash("sha256").update(info.title).digest("hex").slice(0, 12)
    const directory = path.join(root, "others/reports/b-ui")
    fs.mkdirSync(directory, { recursive: true })
    const value = { test: info.title, expected, origins: [...audit.origins], browser_requests: audit.requests }
    fs.writeFileSync(path.join(directory, `api-origins-${key}.json`), JSON.stringify(value, null, 2) + "\n")
    expect(value.browser_requests).toBeGreaterThan(0)
    expect(value.origins).toEqual([expected])
  })
}
