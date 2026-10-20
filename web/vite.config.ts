import path from "node:path"
import fs from "node:fs"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

export default defineConfig({
  base: "./",
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  plugins: [react(), tailwindcss(), {
    name: "safelab-license-notices",
    closeBundle() {
      fs.cpSync(path.resolve(import.meta.dirname, "../others/licenses"), path.resolve(import.meta.dirname, "dist/licenses"), { recursive: true })
    },
  }],
  build: { outDir: "dist", emptyOutDir: true },
  server: { strictPort: true, port: 5173 },
})
