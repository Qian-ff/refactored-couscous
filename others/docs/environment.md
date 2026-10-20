# 本机环境记录

检查日期：2026-10-20。可重复运行 preflight.py；本机详细报告位于忽略的 others/reports/preflight.json。

| 项目 | 本次结果 |
|---|---|
| Git | 2.56.0.windows.1 |
| Node.js | 24.14.0 |
| pnpm | 11.25.0；当前 Codex 终端可发现 |
| 默认 python | 3.10.11，用于标准库准备工具 |
| Python launcher | 可发现 3.14、3.13、3.10、3.8 |
| JDK | 21.0.12，可直接调用 |
| Android SDK | D:/AndroidSDK；已有平台和构建组件 |
| GPU | RTX 5060 Laptop，8151 MiB 显存，驱动 582.05 |
| Docker 客户端 | 29.8.1 |
| Docker 引擎 | Linux Engine29.8.1实际运行，PostgreSQL18健康；API与持久化验证通过 |
| 业务环境 | Python3.14.6 / uv0.13.1 / 本项目独立.venv，冻结安装与18项真实数据库测试通过 |
| 前端与客户端 | pnpm冻结安装；React19.2.8 / Vite8.2.0 / Electron44.9.0 / Capacitor8.5.3 实际构建运行通过 |
| Android 构建 | Gradle8.14.3 / AGP8.13.0 / API36，debug及未签名release实际构建通过 |
| 模拟器 | Emulator37.1.11 / Google APIs x86_64 r07 / SafeLab_API36 / WHPX实际运行通过 |
| AI 推理环境 | A1未安装；worker Python由 A/C/E单独验证和锁定 |

## 当前终端环境

本机 PATH 默认 Java 与已装 JDK21 不一致，因此准备了会话级设置脚本，不修改系统环境变量。主工作区忽略的 local.json 记录已确认路径，子工作区可读取同一份配置。

~~~powershell
. .\others\scripts\Use-ProjectEnvironment.ps1
java -version
adb version
~~~

仅影响当前 PowerShell。Gradle、uv 和 Electron 下载缓存复用主工作区，不进入 Git。多工作树的 Python、node_modules、配置和账号使用方式见 [共享环境](shared-environment.md)。

preflight.py 本身仅探测工具；应用实际运行证据见 a1-handoff.md 和忽略的 others/reports/a1。本轮验证了 Docker/PostgreSQL、网页、Windows与安卓 APK，未验证麦克风、摄像头、模型与安卓实体机。本项目使用 React/Electron/Capacitor，无需 Flutter。

本项目作者和 origin 已配置，checkpoint-1 与当时 main 已上传；当前本地进展以 git status 为准。下一次按既有授权在 A2 验收完成后推送 checkpoint-2。
