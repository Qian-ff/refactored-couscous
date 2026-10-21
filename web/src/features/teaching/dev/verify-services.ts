import fs from "node:fs"
import path from "node:path"
import { requireService, root, sourceIdentity, webPort } from "../../../../../others/scripts/web-environment.mjs"

export default async function verifyServices() {
  const web = await requireService(`http://127.0.0.1:${webPort}`, sourceIdentity("web"))
  const api = await requireService(process.env.LABCONNECT_API_URL || "http://127.0.0.1:8001", sourceIdentity("api", process.env.LABCONNECT_API_ROOT || root))
  const directory = path.join(import.meta.dirname, ".artifacts")
  fs.mkdirSync(directory, { recursive: true })
  fs.writeFileSync(path.join(directory, "services.json"), JSON.stringify({ web, api }, null, 2))
}
