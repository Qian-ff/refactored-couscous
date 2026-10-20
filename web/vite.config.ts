import path from "node:path"
import fs from "node:fs"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"
import { sourceIdentity, webPort } from "../others/scripts/web-environment.mjs"

const identity = sourceIdentity("web")

export default defineConfig({
  base: "./",
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  plugins: [react(), tailwindcss(), {
    name: "safelab-license-notices",
    configureServer(server) {
      server.middlewares.use("/__labconnect/identity", (_request, response) => {
        response.setHeader("Content-Type", "application/json; charset=utf-8")
        response.end(JSON.stringify(identity))
      })
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "build-info.json", source: JSON.stringify({
        source_sha: identity.source_sha, source_fingerprint: identity.source_fingerprint, contract: identity.contract,
      }) })
    },
    closeBundle() {
      fs.cpSync(path.resolve(import.meta.dirname, "../others/licenses"), path.resolve(import.meta.dirname, "dist/licenses"), { recursive: true })
    },
  }],
  build: { outDir: "dist", emptyOutDir: true },
  server: { strictPort: true, port: webPort },
})
