const path = require('node:path')
const { spawnSync } = require('node:child_process')
const root = path.resolve(__dirname, '../..')
const env = { ...process.env, ELECTRON_CACHE: path.join(root, 'others/cache/electron'),
  electron_config_cache: path.join(root, 'others/cache/electron'),
  ELECTRON_BUILDER_CACHE: path.join(root, 'others/cache/electron-builder') }
if (env.HTTPS_PROXY) { env.ELECTRON_GET_USE_PROXY = '1'; env.GLOBAL_AGENT_HTTP_PROXY = env.HTTPS_PROXY }
for (const [entry, args] of [
  ['electron/install.js', []],
  ['electron-builder/cli.js', ['--win', '--x64', '--dir']],
]) {
  const result = spawnSync(process.execPath, [path.join(root, 'node_modules', entry), ...args],
    { cwd: path.join(root, 'desktop'), env, stdio: 'inherit', windowsHide: true })
  if (result.status !== 0) process.exit(result.status || 1)
}
