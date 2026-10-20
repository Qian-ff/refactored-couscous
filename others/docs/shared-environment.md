# 多工作树共用本机环境

统一入口是 Git 主工作区，当前为 `D:\SafeLabPlatform`。工具通过 Git common directory 定位，不把个人绝对路径写进公共配置。无需把新工作树搬到主目录下；环境共享与 Git 分支独立是两件事。

| 内容 | 存放与使用方式 |
|---|---|
| 数据库、业务 `.env`、账号文件 | 主工作区现有一份；共享脚本在子进程加载配置，报告不输出密钥。演示账号读取主工作区 `others/runtime/demo-accounts.json` |
| 本机 JDK/SDK 配置 | 主工作区 `others/config/local.json`；Use-ProjectEnvironment.ps1 自动回退读取 |
| 业务 Python 依赖 | 共用主工作区 `others/backend/.venv`，A 唯一安装维护；每次运行显式绑定当前工作树源码并验证路径 |
| 前端依赖 | 共用主工作区 `others/cache/pnpm-store`；各树按锁文件离线硬链接建立自己的 node_modules，保留各自包解析、Vite 缓存与构建输出 |
| Gradle、uv、Electron 下载缓存 | 共用主工作区现有缓存；会话设置不改系统环境变量 |
| AI worker | C 确定识别引擎后，由 A/C 单独锁定兼容环境；B/D 无需安装，模型下载仅保存一份 |
| 源码、测试报告、构建产物 | 属于各自工作树；正式三端包由 A 集成后重新构建 |

前端保留 node_modules 的目录结构，包文件通过同盘硬链接复用，新增包会增加实际占用；不是每个工作树重新下载一套。禁止编辑依赖包文件。此入口跳过安装脚本，供网页开发、类型检查和构建；Electron/安卓正式打包使用 A 已完整配置的环境。

业务与 AI worker 的依赖需求不同，分别管理。多个聊天也不能轮流向同一个环境安装不同版本。共享入口核对当前树与 A 的依赖描述和锁文件，发现差异立即停止，由 A 接收依赖提案、更新及验证后发布同步基线。子聊天使用下列入口，避免直接 `uv sync` 改写主环境或 `Bootstrap.ps1` 生成另一套数据库凭据。

## 在各自工作树执行

~~~powershell
. .\others\scripts\Use-ProjectEnvironment.ps1
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
python .\others\scripts\shared_env.py install-web
pnpm run check
pnpm run build:web
~~~

`probe` 必须显示共享解释器和**本工作树** app_source；不要只看到解释器能运行就开始测试。install-web 使用现有缓存，缺少包会明确失败，由 A 补齐；不偷偷更换版本或联网安装。已有 node_modules 后不必每轮重复安装。

运行本分支业务测试：

~~~powershell
python .\others\scripts\shared_env.py backend pytest -q
~~~

该入口从当前树的 `others/backend` 执行，pytest 使用真实本地测试数据库。当前数据库名称固定，A/B/C 的后端测试串行，冲突时入口报错而非互相建表删表；稍后重试即可。需要并行数据库验收时由 A 分配独立数据库，不复用正式演示库测试。

D 的首批界面开发使用 A 的 API（8000）和自己的前端，无需再起后端。当前前端默认端口 5173，已有服务时须先核对属于哪个工作树，不能复用其他树页面作为本分支的运行证据。需要额外端口时先向 A 提出 CORS 范围，再在自己的树启动；不关闭跨域或权限检查。

B/C 临时启动本分支服务时选择空闲端口并协调数据库迁移。公共迁移仍归 A：

~~~powershell
.\others\scripts\Start-Backend.ps1 -Port 8001
~~~

共用同一演示数据库意味着数据修改会被其他树看到；只使用合成账号，不擅自重置、重建或清空数据库。分支未集成接口只由该分支服务提供，其他界面必须显示未配置或等待接入。

这些环境不进入 Git、不打入客户端。干净的新电脑仍按锁文件由 A Bootstrap 建立环境；共用是本机开发优化，不改变三端独立发布方式。

## 本轮验证（2026-10-20）

三个新工作树均已探测到同一个主线解释器和各自 app_source，均离线复用缓存建立前端依赖并通过类型检查（下载数均为 0）；D 工作树实际 build:web 通过。fsutil 核实 React 包文件同时硬链接到共享 store 和 A/B/C/D 的依赖目录。22 项协作/环境检查及通过共享入口运行的 20 项真实数据库测试通过；修改后的 Start-Backend.ps1 在临时端口启动，health 返回真实 PostgreSQL 和契约 0.1.0，随后已停止。AI worker 尚未建立，三端语音尚未在本轮实现或实测。
