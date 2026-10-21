# 安研通

**安研通——实验室安全智能协同管理平台** · LabConnect

让安全管理更智能，让实验协同更畅通。

实验室安全教育与风险反馈平台，面向网页、Windows、安卓，三端共用正式账号、权限和业务数据。

**当前阶段：B1 已集成，真实契约0.3.1；独立设计支线的网页候选等待用户批准。** 先完成既有UI改版并经A验收，再进入C；当前顺序及门禁见 [UI改版协作](others/docs/ui-redesign-coordination.md) 与 [阶段入口](others/docs/a2-start.md)。[B1集成交接](others/docs/b1-handoff.md)、历史 [A0基线](others/docs/a0-handoff.md) / a2-ready 与 [A1交接](others/docs/a1-handoff.md) 保留；本次图片不代表产品已改版或三端已验收。

## 从这里开始

- [A1 使用与一键打开](others/docs/a1-usage.md)：双击 Open-Web.cmd、Open-Windows.cmd、Open-Android.cmd，或 Open-A1.cmd 选择三端；包含登录和课程同步体验流程。
- [B1 阶段验收](others/docs/b1-handoff.md)：Open-B1.cmd 打开内部业务组件预览；Open-B1-API.cmd 打开真实后端联调入口。正式导航由 D 接入。
- [UI改版协作与批准](others/docs/ui-redesign-coordination.md)：设计任务登记、网页候选状态、原D/B/F迁移分工和后续frontend-design规则。
- [设计基线](others/docs/design.md)：本聊天确认的功能、范围、数据和视觉要求。
- [A1 状态与交接](others/docs/a1-handoff.md)：已验证证据、待完成项目和可发布基线。
- [开工与交接](others/docs/start-here.md)：先后顺序及当前状态。
- [A2 开工](others/docs/a2-start.md)：新 B/C/D 工作树、共同起点及分阶段集成。
- [阶段Goal](others/docs/ai/README.md)：已交付B1、待批准后执行的D-UI，以及后续C/B2/完整D目标。
- [共用本机环境](others/docs/shared-environment.md)：复用主工作区配置、Python 依赖和下载缓存。
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

用户已授权 A 在当前、B/C/D完成后的第二轮集成、第三轮集成三个节点推送，规则见 [Git 协作流程](others/docs/git-workflow.md)。checkpoint-1 已上传并保留；新 B/C/D 同步 [a2-start 及后续 A 发布基线](others/docs/a2-start.md)。[三角色工作台与搜索](others/docs/design.md#11-三角色工作台与搜索新增要求待后续模块实现)仍待实现，当前 A1 页面不代表这些功能已经完成。
