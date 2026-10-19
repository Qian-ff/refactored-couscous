# SafeLabPlatform

实验室安全教育与风险反馈平台，面向网页、Windows、安卓，三端共用正式账号、权限和业务数据。

**当前阶段：开工前准备。** 已准备项目约定、目录、设计基线、聊天任务书和本地工作流工具；应用、API、数据库迁移、模型及客户端安装包尚未实现。

## 从这里开始

- [设计基线](others/docs/design.md)：本聊天确认的功能、范围、数据和视觉要求。
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

这些是仓库与协作工具检查，不是业务运行测试。应用启动和打包命令由 A 在框架接入后以真实可执行命令补充。

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

本地 commit 与远端 push 是不同操作；本次准备仅建立本地版本及远端地址。首次发布或推送按用户后续指令执行。
