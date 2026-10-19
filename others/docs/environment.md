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
| Docker 引擎 | 此次未连接到运行中的 Linux Engine，应用服务接入前需启动并再检验 |
| 框架与推理环境 | 尚未安装依赖；worker Python 由 A/C/E 验证后锁定 |

## 当前终端环境

本机 PATH 默认 Java 与已装 JDK21 不一致，因此准备了会话级设置脚本，不修改系统环境变量。主工作区忽略的 local.json 记录已确认路径，子工作区可读取同一份配置。

~~~powershell
. .\others\scripts\Use-ProjectEnvironment.ps1
java -version
adb version
~~~

仅影响当前 PowerShell。Gradle 用户缓存定位到当前工作区 android/.gradle-user-home，不进入 Git。

报告确认的是工具/文件可见性，并未运行 Docker 容器、Flutter、模型、麦克风、摄像头或 APK 构建。SDK 文件存在不等于实际构建已验收。框架接入时先验证依赖、许可证和构建，再补全运行说明。

Git 远端已通过只读 ls-remote 验证可达且尚无 HEAD；本项目作者和 origin 已配置。远端 push 尚未执行。
