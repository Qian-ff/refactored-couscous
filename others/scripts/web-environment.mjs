import { execFileSync } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")
const git = (...args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8" }).trim()
export const primaryRoot = path.dirname(path.resolve(root, git("rev-parse", "--git-common-dir")))
const ports = { main: 5173, "codex/b-core-a2": 5174, "codex/c-content-ai-a2": 5175, "codex/d-learning-ui-a2": 5176 }
export const webPort = Number(process.env.LABCONNECT_WEB_PORT || ports[git("branch", "--show-current")] || 5173)
export function sourceIdentity(surface, selectedRoot = root) {
  return JSON.parse(execFileSync("python", [path.join(selectedRoot, "others/scripts/provenance.py"),
    "--root", selectedRoot, "--surface", surface], { encoding: "utf8" }))
}
export function demoAccounts() {
  return JSON.parse(fs.readFileSync(path.join(primaryRoot, "others/runtime/demo-accounts.json"), "utf8"))
}
export async function requireService(url, expected) {
  const suffix = expected.surface === "api" ? "/api/v1/dev/identity" : "/__labconnect/identity"
  const response = await fetch(url.replace(/\/$/, "") + suffix, { signal: AbortSignal.timeout(5000) })
  if (!response.ok) throw new Error(`Cannot verify ${expected.surface} service: HTTP ${response.status}`)
  const actual = await response.json()
  const different = Object.keys(expected).filter(key => actual[key] !== expected[key])
  if (different.length) throw new Error(`Service belongs to another or stale checkout: ${different.join(", ")}`)
  return actual
}
