# Windows desktop

Electron44.9.0 共享网页客户端。A1 提供可搬移测试包；F 接管并扩展安全存储、设备能力和正式安装器。

根目录运行 `pnpm run build:desktop`。完整复制 desktop/release/win-unpacked 文件夹后，运行 LabConnect.exe；不可只拷贝单个 exe。客户端在进程内启动仅监听本机的静态资源服务，业务连接独立后端，运行时不读取开发目录。

根目录运行 `pnpm --filter @safelab/desktop run test`：将包复制到独立目录并实际启动、登录、创建课程，再由真实浏览器用另一账号验证数据可见；截图与结果在 others/reports/a1。凭据从忽略的合成账号文件读取，不打进包。

当前不提供正式安装器。渲染进程禁用 Node，启用隔离与沙箱；录音和摄像头暂未接入，默认拒绝权限。F 后续按真实用途扩展。Electron 下载缓存留在项目 others/cache。

默认目标 Windows 10/11 x64；实际支持版本由锁定的 Electron 和安装测试核对。
