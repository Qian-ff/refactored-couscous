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
- 2026-10-25 本轮 `pnpm run check`、`pnpm run build:web`、本轮 Python Ruff 与 `git diff --check` 通过。

## 尚未完成

本候选仍为 WIP，禁止当作 C02/A2 完成：

1. 最终源码/镜像的四格式和恢复复测；`faults.py` 真实60秒超时与强制控制端退出恢复。
2. Caddy 实际匹配/限制及 compose 配置检查。
3. 本树新提交对应的真实 API 来源检查、浏览器 `content-transfer.spec.ts` 字节/哈希/Blob/会话取消测试；新增测试已通过类型检查，尚未运行浏览器。
4. 最终 core/ASR/C 回归、源码/原候选差异及指纹证据归档。
5. A 接收后才激活共享依赖、重建/验证 main 三端。正式 ECS、D 资料 UI、原生资料保存不在当前已完成结论中。

Docker Desktop 安装位置为当前用户目录 `C:/Users/lenovo/AppData/Local/Programs/DockerDesktop/`。
控制端启停脚本核验 PID、启动时间和源码路径；端口来源不符时保留进程。不要按进程名批量停止服务。
