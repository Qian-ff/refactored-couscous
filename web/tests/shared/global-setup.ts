import fs from "node:fs"
import path from "node:path"
import { reportDirectory, primaryRoot, sourceIdentity, requireService, webPort } from "../../../others/scripts/web-environment.mjs"

export default async function globalSetup() {
  const web = await requireService(`http://127.0.0.1:${webPort}`, sourceIdentity("web"))
  const apiRoot = process.env.LABCONNECT_API_ROOT || primaryRoot
  const api = await requireService(process.env.LABCONNECT_API_URL || "http://127.0.0.1:8000", sourceIdentity("api", apiRoot))
  const directory = reportDirectory
  fs.mkdirSync(directory, { recursive: true })
  fs.writeFileSync(path.join(directory, "browser-services.json"), JSON.stringify({ web, api }, null, 2))
}
