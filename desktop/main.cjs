const { app, BrowserWindow, session } = require('electron')
const http = require('node:http')
const fs = require('node:fs/promises')
const path = require('node:path')

const PORT = 48621
let server
let window
if (!app.requestSingleInstanceLock()) app.quit()

app.whenReady().then(async () => {
  const root = app.isPackaged ? path.join(process.resourcesPath, 'web') : path.join(__dirname, '../web/dist')
  const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' }
  server = http.createServer(async (request, response) => {
    try {
      if (request.headers.host !== `127.0.0.1:${PORT}` || !['GET', 'HEAD'].includes(request.method)) {
        response.writeHead(403).end(); return
      }
      const name = decodeURIComponent(new URL(request.url, `http://127.0.0.1:${PORT}`).pathname)
      const file = path.resolve(root, '.' + (name === '/' ? '/index.html' : name))
      if (!file.startsWith(path.resolve(root) + path.sep)) { response.writeHead(403).end(); return }
      const body = await fs.readFile(file)
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https: http://127.0.0.1:*; object-src 'none'; base-uri 'self'; frame-ancestors 'none'" })
      response.end(request.method === 'HEAD' ? undefined : body)
    } catch { response.writeHead(404).end() }
  })
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(PORT, '127.0.0.1', resolve) })
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false))
  window = new BrowserWindow({ width: 1380, height: 900, minWidth: 390, minHeight: 640,
    show: process.env.SAFELAB_TEST_HEADLESS !== '1', backgroundColor: '#f5f8fa',
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } })
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== `http://127.0.0.1:${PORT}`) event.preventDefault() })
  await window.loadURL(`http://127.0.0.1:${PORT}`)
}).catch(error => { console.error('Client startup failed:', error.message); app.quit() })
app.on('window-all-closed', () => app.quit())
app.on('before-quit', () => server?.close())
