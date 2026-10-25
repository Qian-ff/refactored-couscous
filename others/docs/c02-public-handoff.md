# C02 公共接入候选（A副，未接收）

执行树：`D:/codex/worktree/0aed/SafeLabPlatform`，分支 `codex/a-executor`。
授权工作包：[c02-public-integration](ai/c02-public-integration.md)；执行起点
`e42dee58eefdeadf1fb5bbd462fefe47c8331703`，原 C 候选
`ecb7129497d1f6a69daf09df6db3f2f30537d7ba`，接收 merge `d5e566cae01c1ddae443e70ef483364087568224`。
公共契约 0.4.0 是本树候选；main / ECS 的既有版本不因本文件改变。

## 实现与运行

- 静态 Alembic 头 `c02d0c00001`；API 运行角色与迁移所有者分离。
- `others/scripts/content_candidate_env.py` 管理本树独立业务/worker 验证环境；未覆盖主树共享环境。
- 私有控制端 `others/deploy/content/control.py` 和固定 Docker 解析入口；不向解析器提供数据库、AI 凭据或宿主 socket。
- `Open-C02-API.cmd` / `others/scripts/Start-C02.ps1` 为真实开发 API 入口（8002），资料 UI 由 D 另交付。
- 忽略的配置位于 `others/runtime/c02-public/`。管理配置不得交给 API；不得提交配置、合成账号口令或课件原件。
- 生产 compose/Caddy 为候选配置，尚未部署；Linux socket 控制端部署和云端卷恢复尚未实测。

## 现有真实证据

本树忽略的 `others/reports/c02-public/` 保存证据，不能用能力声明代替实测。

- worker 四格式 18 项；C 领域纯检查 40 项。
- PostgreSQL 领域/角色 53 项与 55 subtests；目标投影 5 项。
- 真实 HTTP 流程和克隆库迁移共 5 项：上传/重解析、审核发布、撤权、跨校、版本、接收并发与取消；B1 升级、重复升级、空库和专用克隆 downgrade/re-upgrade。见 `http-migration-recovery.txt`。
- `stress.json`：真实 384MiB OOM、pids64、1CPU 节流、封存输入20MiB及44MiB临时区、stdout16MiB/stderr64KiB上限。
- `linux-lock.json`：真实 Linux Docker 数据卷，独立进程互斥、释放接管、稳定锁 inode。
- `faults.json`：真实暂停解析61秒触发60秒期限、确认停止；强制退出本树控制端后恢复、拒绝旧任务迟到启动、新任务成功。
- `sandbox.json`：原候选镜像四格式、同绑定重放/异绑定拒绝、实际权限拒绝、双客户端互斥、接收中停止、重启终止凭据。此报告仅标记自身检查范围；资源/HTTP由独立报告证明；返修后新镜像见 `sandbox-review-fix.json`。
- `gateway.json`：真实 Caddy 与合成消费正文上游，11项路径/方法/上传22020096字节与其他路径2000000字节边界、公开文档404。仅本机测试，非 ECS 证据。
- `compose-check.json`：Docker compose真实解析（空占位env、tools profile），未部署。
- `backend-regression.txt`：完整公共、core、content共152项及55 subtests；`asr-regression.txt`：既有ASR传输回归4项（不等同真实语音推理）。
- `web-tests.json`、`browser-services.json`：真实浏览器生成SDK原始上传下载字节/哈希、Blob、长度、UTF-8文件名、旧请求取消及无权JSON错误；测试时API源码为`e3fd83d34b6507b17aba84abebeba79d753823ad`。
- 2026-10-25 本轮 `pnpm run check`、`pnpm run build:web`、真实contracts check、本轮 Python Ruff、候选环境工具2项与 `git diff --check` 通过。

## A 第一轮审查返修

A 审查提交 `8ebaa7a2c3782fe3c1c1fc9ad1cfe1b01bbcef22`，代码修复提交
`d56191b2b743504dd7f09d0503f6e4d377680395`。原候选存在不安全输出读取和分片管道截断，原有测试不能覆盖这两项。

- `output_files.py` 统一读取 status/result/accepted。Linux 用逐级 `dir_fd`、`O_NOFOLLOW`、`O_NONBLOCK`；Windows 用禁止删除共享的目录句柄固定路径、`FILE_FLAG_OPEN_REPARSE_POINT`、磁盘文件类型和句柄元数据检查。拒绝重解析点/符号链接、硬链接及特殊文件；同一已校验句柄限量读取并核对前后 inode/大小/链接数/时间。result 发送前重新验证，发送期间保持 release 互斥。
- 容器接收凭据改为临时文件 fsync 后原子替换，控制端检查实际输入哈希、长度和 kernel seals，避免读取未完成的接收凭据。
- Docker stdout/stderr 独立循环读至 EOF，各自累计上限仍为64KiB；超限或12秒超时终止、关闭管道并回收子进程，避免满管道导致 wait 挂起。缺对象仍须 Docker 健康才能确认不存在。
- 长期回归：`others/deploy/content/test_control_boundary.py`。可用独立候选 Python 执行 `-m unittest discover -s others/deploy/content -p test_control_boundary.py -v`。Linux验证只读挂载五个必要源码，无配置/资料库，用隔离tmpfs生成合成链接/FIFO/设备。
- `review-fix-windows.txt`：15项中13项适用并通过，2项POSIX特殊文件不适用；实际Windows文件/目录符号链接、硬链接和替换测试均执行。`review-fix-linux.txt`：15项全部通过。输出协议测试仅桩表示容器退出，真实内核文件句柄与真实分片/超限/超时子进程均执行，不冒称真实恶意容器攻击。
- 新镜像 `sha256:8f03fd2feddb4df71cef70c4f7a8c0520aba2e716f8736d77f668b6833ea25b3` 来自修复提交 `d56191b2`，闭包指纹 `22d6db8962f16d34f7eac8b60044ab5cff9c44097a383e5c3b8b6add2750bd51`。`sandbox-review-fix.json`、`stress-review-fix.json`、`faults-review-fix.json`分别记录本轮四格式/屏障、资源和恢复复测。历史 `sandbox.json` 按上一轮索引哈希逐字节保留，历史manifest另存 `final-manifest-e43da754.json`。
- 最终提交的真实API、HTTP/浏览器和源码索引，以 `final-manifest.json` 为准；不把旧API来源或镜像构建SHA冒称最终运行SHA。

## 接收与剩余边界

后台技术候选交 A 审核，禁止当作 C02/A2 完成：

1. 最终提交后的 API 来源、真实HTTP及共享会话回归见同证据根和`others/reports/c02-review-final/`；原候选逐文件 blob、授权修复差异及最终源码指纹归档至本树忽略证据根。
3. A 接收后才激活共享依赖、重建/验证 main 三端。正式 ECS、D 资料 UI、原生资料保存不在当前已完成结论中。

历史镜像`sha256:85b4a147c6a394ccad23873c1b7bdf04a27aac3a65f210261d0c9e5cf5d3f4ab`来自`a3f0d8300b92bb8f20003dba771176b6d64aece7`构建，不再作为本轮控制端解析镜像；原Linux边界单测曾使用此镜像的Python和隔离tmpfs运行修复后只读源码，与新解析镜像集成验证区分。

Docker Desktop 安装位置为当前用户目录 `C:/Users/lenovo/AppData/Local/Programs/DockerDesktop/`。
控制端启停脚本核验 PID、启动时间和源码路径；端口来源不符时保留进程。不要按进程名批量停止服务。
