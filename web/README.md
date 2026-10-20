# Web / shared UI

React/TypeScript/Vite/Tailwind/shadcn 共享界面，A1 提供学校账号登录、当前身份、课程列表与授权创建。关卡、助手和培训记录明确标为待接入。

D 管理公共组件、入口、导航与学生体验；B/C/E 管理各自业务页面，F 管平台适配，A 管生成客户端和公共依赖。精确范围见 ../others/contracts/ownership.json。

在仓库根目录：`pnpm run dev` 启动网页，`pnpm run build:web` 生成用于 HTTPS 服务的 dist；`pnpm run build:debug` 生成允许指定本机地址 HTTP 的测试产物；`pnpm run test:web` 在真实浏览器执行 A1 流程。Windows 本机测试自动复用已安装 Edge，其他环境先用 Playwright 官方安装命令准备 Chromium。

修改服务端接口后，A 运行 `pnpm run generate-client`，再运行 `pnpm run check:contracts` 校验真实 OpenAPI 与 SDK；不要手改 src/client 生成文件。服务地址在登录页设置，登录凭据仅存内存；刷新或重开需登录。

dist 用于独立网页部署，也供 Electron/Capacitor 打包；后端在 others/backend 单独部署。源码构建需要完整仓库，部署的客户端不读取开发目录。许可文本随 dist/licenses 交付。
