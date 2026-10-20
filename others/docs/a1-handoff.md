# A1 三端共享底座交接

状态：**A1 必需验收通过，可以交接后续模块。** 品牌为安研通 / LabConnect。A1 实现账号、授权和基础课程；完整教学、AI 与监控由后续模块实现。

实现与验收代码提交：`7fef37d0fa47f8172fc96294c20615b4559e55c7`。最初验收基线为固定标签 **`a1-0.1.0`**。后续增加了可见模拟器与三端一键启动；本轮再明确三角色工作台、课件搜索和推送要求。当前新聊天使用 **`checkpoint-1`**，执行 `git rev-parse checkpoint-1` 取得完整 SHA。初始验收时仅本地提交；当前及后续推送授权见 git-workflow.md。

契约版本 `0.1.0`，状态 implemented；OpenAPI SHA256 `2fb5156d12ca6a46e611519a39134e07b2315493e80405a547de80bc15fea949`。公开模型以真实 SQLModel/Alembic 为准，路由见 others/contracts/openapi.json。来源与许可见 upstream.md、licensing.md。

| 验收项 | 当前证据 |
|---|---|
| 职责与协作工具 | 首批修正提交 0e89a1f；9 项真实 Git 工作流测试通过 |
| PostgreSQL 与初始迁移 | 官方 PostgreSQL18 镜像已启动，初始迁移 c7d7105add2f 已实际执行 |
| 授权与业务接口 | 18 项 PostgreSQL 后端测试通过；学校、学院、课程范围、角色撤销、退出和数据库外键约束已验证 |
| 服务重启持久化 | 已重启后端及 PostgreSQL 容器，先前经 API 写入的课程仍可由同校授权账号读取，跨校读取被拒绝 |
| 真实契约 | 0.1.0；已导出 OpenAPI 并生成客户端，确定性检查通过 |
| 网页 | TypeScript、调试构建与 3 项真实浏览器测试通过；已验证创建/跨账号读取、390px 布局、退出、错误密码和网络失败 |
| Windows | 安研通/LabConnect 可搬移测试包已构建，从独立复制目录实际启动、登录和创建课程，浏览器另一账号可读取；渲染进程未开放 Node |
| Android | 调试 APK 已实际构建、安装并启动；API36 Google APIs x86_64 r07 / SafeLab_API36 / WHPX 实测，安卓读取 Windows 创建课程，与网页双向创建/读取；原生触摸退出、学生范围、无横向溢出及原生界面无遮挡均通过 |
| 发布网络边界 | 未签名 release 实际构建成功；包内配置及合并 Manifest 验证 cleartext=false、mixedContent=false、debuggable=false；debug/release 依赖均进入原生锁文件 |
| 包与凭据 | 三个归档的 ZIP CRC 检查通过，哈希见 artifacts.json；品牌和许可随包保留；Git 源码及客户端资源未包含本机实际数据库口令、服务主密钥或合成账号密码 |
| 固定依赖 | pnpm/uv 冻结安装通过；生产网页构建和 TypeScript 检查通过；FastAPI 模板来源、适配和 MIT 原文已记录 |

验证日期：2026-10-20。本机证据位于被忽略的 others/reports/a1：persistence.json、web-tests.json、windows-test.json、android-test.json、release-policy.json、artifacts.json，以及 web-*.png、windows-packaged.png、android-device.png。登录密码仅在被忽略的 others/runtime/demo-accounts.json，不进入报告或客户端包。

## 本机交付物

| 类型 | 路径 |
|---|---|
| 生产模式网页 | web/dist；归档 web/release/LabConnect-0.1.0-a1-web.zip |
| Windows 可搬移测试包 | desktop/release/LabConnect-0.1.0-a1-win-x64.zip；解压后运行完整文件夹中的 LabConnect.exe |
| 安卓调试 APK | android/release/LabConnect-0.1.0-a1-debug.apk；构建原件 android/native/app/build/outputs/apk/debug/app-debug.apk |

这些是本机忽略产物，其他 checkout 需重新构建。客户端安装后不依赖开发目录；共享后端仍需独立运行。每种客户端构建会重生成共享 web/dist，部署网页前重新执行 `pnpm run build:web`；已归档的三个文件相互独立。

## 启动与合成账号

在 D:\SafeLabPlatform 的 PowerShell 中首次准备环境；已有 Docker Desktop 需处于运行状态：

~~~powershell
./others/scripts/Bootstrap.ps1
docker compose --env-file .env -f others/deploy/compose.yml up -d --wait db
& ./others/backend/.venv/Scripts/python.exe -m alembic -c others/backend/alembic.ini upgrade head
Push-Location others/backend
& ./.venv/Scripts/python.exe -m app.seed
Pop-Location
./others/scripts/Start-Backend.ps1
~~~

另开终端运行 `pnpm run dev`，打开 http://127.0.0.1:5173。后端默认8000，PostgreSQL仅本机55432。停止容器保留数据卷；生产环境禁止运行 seed。

学校代码 demo-a：admin、college、teacher、teacher_eng、student、student_chem；demo-b：admin_b、teacher_b；platform：platform。随机密码从 others/runtime/demo-accounts.json 取得。性别/联系方式等完整档案和账号业务由 B 后续扩展。

## 构建与复验

后端与网页开发服务保持运行；先做 Windows 测试，再做安卓测试，后者会检查 Windows 创建的课程。

~~~powershell
pnpm run check:contracts
pnpm run check
pnpm run build:web
pnpm run test:web
pnpm run build:desktop
pnpm --filter @safelab/desktop run test
pnpm run build:android
# 按 android/README.md 启动 SafeLab_API36 后：
pnpm --filter @safelab/android run test
~~~

后端测试在 others/backend 执行 `./.venv/Scripts/python.exe -m pytest -q`，使用本机专用 safelab_a1_test，用例回滚各自写入；多个聊天按批串行运行此测试库。测试覆盖不同角色、跨校读写、学院越界、跨学院最小数据、退出撤销、授权撤销/停用立即生效、伪造学校字段、数据库外键及同校管理员一致性。

准备检查：`python others/scripts/check_preparation.py`；Git工作流测试：`python -m unittest discover -s others/qa -p 'test_*.py' -v`。契约校验会从实际应用重新导出 OpenAPI 并生成临时 SDK 比较，不靠手写接口通过。

调试安卓使用 http://10.0.2.2:8000；HTTP例外仅指定本机地址。生产网页和安卓 release 要求 HTTPS，不预填云服务。`./others/scripts/Build-Android.ps1 -Release` 会同步生产网页；产出尚未签名。

## 后续聊天与主对话测试

先并行 B/C/D，连同总控 A 最多四个。B 负责核心及学习考试后端，C 负责资料/题库/语音，D 接管前端入口、路由及学习体验。E/F 在相应基线可用且有空位后扩展监控、原生能力和正式安装器；G 在集成后独立实测。完整任务书见 others/docs/ai。

B–G 原工作区仍保留准备提交，尚未同步。每个聊天只在自己的 worktree/task 分支操作，先保留已有改动，在干净分支执行：

~~~powershell
git status --short
git merge checkpoint-1
python others/scripts/workflow.py status --baseline checkpoint-1
~~~

必须看到当前工作区 contains_baseline=true、contract_version=0.1.0 才开始。选择共用本机开发数据库时，先将主工作区被忽略的 .env 私密复制到自己的 .env，再运行 Bootstrap；不启动第二套同端口 Compose，不覆盖主工作区配置。各自虚拟环境、缓存与模型留在忽略区。

接口或持久模型变化先交 A 协调；A 一起发布迁移、实现、OpenAPI 与 SDK，D 注册页面。每轮检查并提交，回报 SHA、契约影响及剩余工作。**B/C/D 首批模块提交后回本主聊天做 A2 集成；E/F 接入后回本聊天做三端联调，最终交 G 独立验收。**

## 已知限制与恢复记录

- 安卓仅验证上述模拟器，尚未验证实体机、长期稳定性或全部系统版本；Windows 正式安装器、发布签名由 F 扩展。
- 首次模拟器开机出现过网络未就绪与 System UI 无响应弹窗。已恢复，保留 android-device-systemui-anr.png，并补充网络就绪、原生无遮挡和真实触摸检查后通过。不能据此宣称所有设备稳定性已验证。
- Docker Engine 曾停止，具体原因未确定；本轮恢复后读写与持久化复验通过。数据库容器配置 restart:unless-stopped 和512MiB上限。
- 后端测试有 Starlette/httpx 废弃提示、Capacitor Gradle 有 flatDir 提示，目前不影响通过；依赖调整须由 A 协调锁文件和复验。
- CI 已适配 pnpm/uv 并固定 Action 提交，但未推送触发远端 CI；后端 Dockerfile 已适配且构建上下文只包含公开源码，本轮未单独构建后端镜像。本机真实数据库和API已运行验证。
- 完整教学考试、AI审核/语音、监控、学校密钥加密、备份恢复和正式 HTTPS 部署留给后续阶段；未开放入口已有真实状态提示。
