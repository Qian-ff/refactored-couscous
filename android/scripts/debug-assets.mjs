import fs from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '..')
const source = path.join(root, 'native/app/src/main/assets/capacitor.config.json')
const config = JSON.parse(fs.readFileSync(source, 'utf8'))
config.android = { ...config.android, allowMixedContent: true }
config.server = { ...config.server, cleartext: true }
const destination = path.join(root, 'native/app/src/debug/assets')
fs.mkdirSync(destination, { recursive: true })
fs.writeFileSync(path.join(destination, 'capacitor.config.json'), JSON.stringify(config, null, 2) + '\n')
console.log('Prepared debug-only loopback HTTP configuration; release remains HTTPS')
