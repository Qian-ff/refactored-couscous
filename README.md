# 安研通

**安研通——实验室安全智能协同管理平台** · LabConnect

让安全管理更智能，让实验协同更畅通。

实验室安全教育与风险反馈平台，面向网页、Windows、安卓，三端共用正式账号、权限和业务数据。

**当前阶段：A1 三端共享技术底座验收通过。** 真实 PostgreSQL、账号/授权/基础课程、网页、Windows 测试包与安卓模拟器均已实际运行；固定交接基线 `a1-0.1.0`、命令及证据见 [A1 交接报告](others/docs/a1-handoff.md)。完整教学、语音与监控由后续模块扩展。

## 从这里开始

- [A1 使用与一键打开](others/docs/a1-usage.md)：双击 Open-Web.cmd、Open-Windows.cmd、Open-Android.cmd，或 Open-A1.cmd 选择三端；包含登录和课程同步体验流程。
- [设计基线](others/docs/design.md)：本聊天确认的功能、范围、数据和视觉要求。
- [A1 状态与交接](others/docs/a1-handoff.md)：已验证证据、待完成项目和可发布基线。
- [开工与交接](others/docs/start-here.md)：先后顺序及当前状态。
- [本机环境](others/docs/environment.md)：实际工具检查、会话级 JDK/SDK 设置与未验证项。
- [七个 AI 聊天任务](others/docs/ai/README.md)：复制对应任务书到聊天。
- [Git 与分支协作](others/docs/git-workflow.md)：每轮提交、独立工作区和合并。
- [验收清单](others/qa/acceptance.md)：将来应用必须通过的检查。
- [配置模板](others/deploy/.env.example)：占位配置，实际密钥保存在忽略文件中。

## 当前可运行的准备检查

在项目根目录的 PowerShell 中：

~~~powershell
python .\others\scripts\check_preparation.py
python .\others\scripts\preflight.py --report .\others\reports\preflight.json
python -m unittest discover -s .\others\qa -p "test_*.py" -v
python .\others\scripts\workflow.py status
~~~

这些是仓库与协作工具检查。应用准备及数据库启动见 [后端说明](others/backend/README.md)。另开终端执行 `./others/scripts/Start-Backend.ps1` 与 `pnpm run dev`。网页使用 http://127.0.0.1:5173；合成账号见忽略的 others/runtime/demo-accounts.json。

在根目录执行 `pnpm run build:desktop` 构建 Windows 测试包，`pnpm run build:android` 构建安卓调试 APK。三端具体命令与阶段状态见各端 README；构建成功和实际运行通过分别记录。

## 目录与交付

| 目录 | 职责 |
|---|---|
| web | 共享界面与网页构建 |
| desktop | Electron 与 Windows 安装包 |
| android | Capacitor 与安卓原生工程 |
| others | 后端、推理、契约、部署、设计、验收及忽略的本地工作副本 |

三个客户端分别发布。构建时使用完整仓库的共享源码；安装后不依赖开发目录。后端和监控节点另行部署，客户端通过服务地址连接。仅拷贝一个源码目录重新构建不属于当前保证范围。

## Git

每轮代码生成或修改完成，运行必要检查并提交本轮相关改动；分支聊天提交到自己的分支。提交后回报分支、提交 ID 和检查结果。远端已指定为：

https://github.com/Qian-ff/refactored-couscous.git

本地 commit 与远端 push 是不同操作；每轮保存本地提交，远端推送由 A 按已授权节点执行。

用户已授权 A 在当前、B/C/D完成后的第二轮集成、第三轮集成三个节点推送，规则见 [Git 协作流程](others/docs/git-workflow.md)。当前后续聊天同步 checkpoint-1，包含最新一键工具及[三角色工作台与搜索要求](others/docs/design.md#11-三角色工作台与搜索新增要求待后续模块实现)。搜索和角色独立工作台仍由 B/C/D 等后续模块实现，当前 A1 页面不代表这些功能已经完成。
