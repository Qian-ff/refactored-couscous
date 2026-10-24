# 安研通

**安研通——实验室安全智能协同管理平台** · LabConnect

让安全管理更智能，让实验协同更畅通。

实验室安全教育与风险反馈平台，面向网页、Windows、安卓，三端共用正式账号、权限和业务数据。

**当前阶段：[v3首版交付流程](others/docs/delivery-workflow.md)已发布，A副接C02后端/worker、D接资料前端，C准备后续题库/关卡。** [c-start-ready交接](others/docs/cloud-asr-handoff.md)记录实际部署、AI/语音私有连接、鉴权/超时/取消/清理与故障恢复；B2等真实固定内容版本、学生DTO和受控答案服务由A接收后放行。真实契约0.3.2；双击Open-DUI.cmd打开现有网页，Start-CloudASR.cmd恢复本机识别节点。题库、考试、助手、监控及未来工作台尚未开放。[既有UI](others/docs/existing-ui-acceptance.md)、[D第一批](others/docs/d-ui-foundation-handoff.md)、[B1](others/docs/b1-handoff.md)、[A0](others/docs/a0-handoff.md)及[A1](others/docs/a1-handoff.md)保留历史证据，不混用阶段结论。

## 从这里开始

- [多聊天协作规范](others/docs/coordination.md)：A主、A副、B/C/D/G；E并C、F并A副。v3保留自查/里程碑规则，新增C02责任移交及C前端统一交D；业务和历史证据保留。[实际迁移与接收记录](others/docs/coordination-rollout.md)。

- [A1 使用与一键打开](others/docs/a1-usage.md)：双击 Open-Web.cmd、Open-Windows.cmd、Open-Android.cmd，或 Open-A1.cmd 选择三端；包含登录和课程同步体验流程。
- [既有UI验收与本轮入口](others/docs/existing-ui-acceptance.md)：Open-DUI.cmd、学生加退班/历史演示、三端实测、安卓返回回归及C前置边界。
- [B-UI正式页面体验与D接续](others/docs/b-ui-integration-handoff.md)：Open-BUI.cmd打开当前正式界面，区别于历史B1独立组件夹具；本地基线b-ui-integrated。
- [学生本人关系接口交接](others/docs/student-relations-handoff.md)：0.3.2真实接口、生成SDK、D接续条件及项目内pnpm恢复；Open-StudentRelations.cmd启动同一套现有网页/API。
- [B1 阶段验收](others/docs/b1-handoff.md)：Open-B1.cmd 打开内部业务组件预览；Open-B1-API.cmd 打开真实后端联调入口。正式导航由 D 接入。
- [D-UI执行交接](others/docs/ui-redesign-execution.md)：已批准桌面与冻结SHA、D/B/A副当前文件分工（历史F由A副接收）、公共组件先行和C/B2验收门禁。
- [悬浮助手 v1.1 接收交接](others/docs/assistant-floating-handoff.md)：已批准的三端应用内单例规范、D/C/A副/B2职责和后续目标；仍待产品实施。
- [UI网页图册](others/design/ui-redesign/index.html)、[390px移动图册](others/design/ui-redesign/mobile-gallery.html)：已接收的设计参考，非产品运行证据；持续规则见[UI改版协作](others/docs/ui-redesign-coordination.md)。
- [设计基线](others/docs/design.md)：本聊天确认的功能、范围、数据和视觉要求。
- [A1 状态与交接](others/docs/a1-handoff.md)：已验证证据、待完成项目和可发布基线。
- [开工与交接](others/docs/start-here.md)：先后顺序及当前状态。
- [A2 开工](others/docs/a2-start.md)：新 B/C/D 工作树、共同起点及分阶段集成。
- [阶段Goal](others/docs/ai/README.md)：已交付B1、当前D-UI和依赖公共组件的B-UI，以及后续C/B2/完整D目标。
- [共用本机环境](others/docs/shared-environment.md)：复用主工作区配置、Python 依赖和下载缓存。
- [ECS 云端联调部署](others/deploy/cloud/README.md)：从干净主线打包、独立凭据、HTTPS、数据库备份与迁移；实际地址、版本与三端验证见[云端交接](others/docs/cloud-handoff.md)。
- [C开工与云端ASR前置](others/docs/cloud-asr-handoff.md)：c-start-ready基线、私有适配、一键启停、云端/本地验证及后续权限边界。
- [本机环境](others/docs/environment.md)：实际工具检查、会话级 JDK/SDK 设置与未验证项。
- [六个协作身份与任务](others/docs/ai/README.md)：复制对应任务书到聊天。
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
