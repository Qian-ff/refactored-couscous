import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '../..')
const output = path.join(root, 'others/licenses')
fs.mkdirSync(output, { recursive: true })
const seen = new Map()
function resolvePackage(name, from) {
  let current = from
  while (current.startsWith(root)) {
    const candidate = path.join(current, 'node_modules', name, 'package.json')
    if (fs.existsSync(candidate)) return candidate
    const parent = path.dirname(current)
    if (parent === current) break
    current = parent
  }
  throw new Error('Missing installed dependency: ' + name)
}
function visit(name, from = root) {
  const file = resolvePackage(name, from)
  const metadata = JSON.parse(fs.readFileSync(file, 'utf8'))
  const id = metadata.name + '@' + metadata.version
  if (seen.has(id)) return
  const directory = path.dirname(file)
  const notices = []
  for (const name of fs.readdirSync(directory).filter(name => /^(licen[sc]e|notice)(\.|$)/i.test(name))) {
    if (!fs.statSync(path.join(directory, name)).isFile()) continue
    const destination = id.replace(/[^\w.-]/g, '_') + '-' + name + '.txt'
    const notice = fs.readFileSync(path.join(directory, name), 'utf8').trimEnd() + '\n'
    fs.writeFileSync(path.join(output, destination), notice)
    notices.push(destination)
  }
  seen.set(id, { name: metadata.name, version: metadata.version, license: metadata.license || 'See upstream',
    source: typeof metadata.repository === 'string' ? metadata.repository : metadata.repository?.url,
    noticeFiles: notices })
  for (const child of Object.keys(metadata.dependencies || {})) visit(child, directory)
}
for (const name of ['react', 'react-dom', 'axios', '@radix-ui/react-slot', 'class-variance-authority', 'clsx',
  'tailwind-merge', 'lucide-react', 'react-router', '@capacitor/core', '@capacitor/android', 'electron', '@hey-api/openapi-ts']) visit(name)
fs.writeFileSync(path.join(output, 'npm-runtime.json'), JSON.stringify([...seen.values()].sort((a, b) => a.name.localeCompare(b.name)), null, 2) + '\n')
console.log(`Recorded ${seen.size} installed packages and their shipped license notices`)
