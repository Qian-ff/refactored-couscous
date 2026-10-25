# C1 T2：真实任务、统一计量和公共接口接入

编号 `c1-runtime-public-integration`，2026-10-26由A主启用。是用户已首启C1的后续公共接入，按gpt-6.1-sol / medium / Default实施；不重开首次Plan或Goal。A副的具体权限来自main已提交active委托及A实际发送的完整执行SHA。

## 输入、身份与完成目标

执行者：A副 / A-executor，host=local，thread `01a16921-9ff8-7781-bdb8-6ede3d015d6c`，登记树 `D:/codex/worktree/0aed/SafeLabPlatform`、分支 `codex/a-executor`。先读[统一规范](../coordination.md)、[工作包模板](work-package-template.md)、[共享环境](../shared-environment.md)、[契约入口](../../contracts/README.md)、[Git流程](../git-workflow.md)、[首版路线](../delivery-workflow.md)及[当前接收记录](../c1-domain-reception.md)。

main代码起点 `d4a328bb0fb9742d3d981c20c68f7cff3be5fa3a`，实际开工还须包含A消息的规则发布SHA。领域候选 `46394d57fc077e381748acb306e133476a47e7fe` 已含T1 `db0ca18e5c0bf4fae1558755b702b7e4ddc2669a` 和C行锁修复，15项真实领域PG及最终受影响夹具2项已通过；A接受为T2输入，不是main、HTTP、SDK或runner通过。普通合并准确SHA，保留843/671/db0ca/463历史。

候选内 `others/docs/c1-public-handoff.md`、`content/questions/handoff/c1-t1-domain.md`、`c1-http-candidate.md`、`c1-transfer-format.md` 和T1包构成接缝说明。旧OS临时只读草案可参考，不代替本包授权。未进main的文件通过 `git show 46394d57fc077e381748acb306e133476a47e7fe:文件路径` 读取，不能把主树缺文件误判成候选缺失。

目标：保留已验证T1和领域语义，提供真实C1运行/HTTP/0.5.0 OpenAPI与生成客户端候选，供A最终接收后发布固定版本、学生安全DTO和B2受控答案服务基线。首版60题/六关仍是待审核草稿，不自动发布或写入主库。

## 1. 独立环境与精确依赖

主线业务/worker共享环境及18767解析器保持。新backend/worker锁先只在A副忽略的 `others/runtime/c1-public/envs/` 准备候选，复用主树uv缓存/解释器和现有源码绑定机制，不覆盖main共享venv，不另建通用环境管理器。现有helper只扩展固定C1 profile/目录/active包验证，必要时用薄C1入口；不得加任意工作树、任意库或跳过锁校验开关。

backend dev补 `openpyxl==3.1.5`、`defusedxml==0.7.1`，不加到API生产依赖。worker补这两项及 `pydantic==2.13.4`，由uv固定全部传递依赖、官方来源、哈希和许可（含et-xmlfile/pydantic-core等实际闭包）。保留全部既有ASR/资料解析精确版本；不顺手升级弃用提示对应库。依赖解析若必须改变既定版本或无法取得许可，带证据交A再决定。

沿用实际 `safelab_c1_test` 非owner profile及owner分离，不用main库或旧C02验收库；共享pytest锁继续串行。候选API8002、前端必要时5177、候选控制端18768（仅本机）；独立任务/日志/存储，保留main8000/5173/18767。更新候选helper/API引导的C1白名单，不取消旧C02默认行为。无需为候选新建付费资源。

## 2. 统一队列、接收和计量

沿用ContentJob与QuestionTransferTask两个固定表，不建第三张通用任务表或新队列服务。旧资料与C1导入/导出双向看到同一全局50/账号5队列上限；同一账号1接收会话、全局2接收槽在同一quota advisory lock内领取，锁序tenant→quota→row。统一选最早可执行任务，保留一个实际重任务、停止屏障与恢复，不只让C1单向读取旧表。

C02配额计入C1保留/存留字节；C1真实ContentBudget与TransferAdmission同样计入C02原件、版本、上传和任务。题目/关卡草稿/固定版本、场景、来源台账、预检、manifest、导出和失败残留明确计量，父canonical已含子载荷的部分不重复。学校/公共1GiB、全局5GiB，工作预留32MiB、扣预留后实际空闲磁盘保底1GiB保持。

每次写操作前新采样剩余磁盘，不在全局quota锁内做磁盘I/O，也不永久缓存启动时容量。C1Environment应由请求级真实采样提供budget/IO，缺环境、配额或准入保持真实503。保留取消后未封存且仍持有接收租约的占用；租约到期、状态取消或文件已删均不能代替句柄关闭、清理提交和预留确认释放。

只允许委托登记的四个C1接缝文件由A副串行修改；其他C域代码/模型/夹具原样接收。需要修其他领域文件时带确切问题交A/C，不越写；不改B的授权策略。

## 3. 三种固定任务与可信结果

在现有受信控制端/协议/runner中增加有限分派 `material_parse`、`question_import`、`question_export`。旧资料任务兼容；C1使用真实task_id和明确类型，不伪造MaterialVersion ID。若协议形状需版本迁移，同步客户端/服务端/示例和实际能力检查，保持候选与main控制端分开，不静默把不支持的服务当成功。

沿用固定模板、单控制器锁/journal、真实execution_id、generation、owner lease、密封输入、安全输出句柄与停止回执。HTTP/任务不能传任意命令、镜像、宿主路径或挂载；API/worker不持Docker socket或owner/云密钥。保留无网、非root、只读根、384MiB/CPU1/pids64和现有有界日志；资料60秒，C1固定30秒。停止/清理不明时不重用代次/槽位。

CLI仅复制纯传输闭包：空包初始化、必要content schemas、questions schemas/transfer_codec/transfer_cli与依赖；不复制API配置/SQLModel/DB/密钥/ASR模型或整个site-packages。最小适配可信密封fd，核对内核密封，替代必须挂宿主/job/input的假设；不暴露任意路径参数。Excel临时目录在导入库前固定为受控/work，继续现有总64MiB tmpfs预算。普通真实CSV/XLSX流转核对受控临时文件与预留，不能宣称覆盖未测压力峰值；实际无法满足32MiB时报A，不静默加预算。

导入：CSV输入1MiB、XLSX5MiB；真实封存输入经受限CLI输出有界Preview，确认执行退出后，在匹配代次/租约下事务写预检，再清理/确认停止/释放预留；不把错误JSON或非0退出当成功。教师确认时沿用原子预检hash/版本/重复校验，不直接发布。

导出：执行前按固定有序版本清单重新鉴权/重算manifest，私有输入16MiB；输出CSV1MiB/XLSX5MiB，验证格式/大小/hash后用自己的guard与.part→.blob封存。匹配代次、实际退出和安全封存后才记成功；下载每256KiB复查当前会话/版本，不在旧授权下复用结果。普通取消/重试必须真实停止旧执行并确认清理/预留，不仅改state。

## 4. 公共HTTP、B2接缝和SDK

候选挂载实际questions/lessons routers并注入真实环境。真实版本唯一来源 `others/config/application.json`，本包候选升0.5.0，导出OpenAPI/版本/hash及生成SDK保持一致；main仍0.4.1直至A接收，不改云端。

输入PUT为实际octet-stream，已封存重复上传409并引导查任务；下载为实际Blob。Caddy只新增精确UUID `PUT /api/v1/content/questions/tasks/{task_id}/input` 的5,242,880字节例外，CSV业务1MiB照旧，不扩大整个content。传输信号、会话代次、鉴权和错误处理复用既有公共层，不建第二套认证/客户端。需SDK二进制适配时只改明确公共文件，保持D既有调用兼容。

实际C1管理/教师预览仅teacher/admin；学生不得直接读取题库答案/草稿/未解锁素材。B2仅通过 `resolve_assessment_questions`、`resolve_lesson_publication` 取已审核固定评分/素材私有快照；学生投影只做安全过滤，实际任务/当前关系/解锁由B2后续验证。不能为导出DTO伪造学生答案HTTP或裸asset/hash静态直链。学生安全DTO/共享类型仅按实际模型对齐，真实生成客户端不加入虚构接口。

教师预览与SVG保持授权、private/no-store/CSP及被动素材规则。D仍唯一前端入口/路由，A副不写D content页面或ApplicationShell；本包不做题库编辑UI、学习考试、助手、监控、原生保存或安装器。

## 5. 实际检查与接棒

M1：候选锁/许可、真实统一计量/接收和固定CLI/控制端闭包可运行。用普通小样本执行各一例CSV、XLSX真实导入预检→确认草稿→教师审核发布→固定版本导出回读，保留进程退出/停止清理/hash/字节与32MiB计量证据。原先跳过的XLSX实际往返必须执行。混合旧资料/C1正常排队、一个常见取消/重试及接收占用回归即可，不追加高级安全、压力/耗尽或复杂故障矩阵。

M2：专用非owner库和真实会话下HTTP/SDK验收上述闭环，覆盖普通跨校/学院/课程拒绝、学生无答案、固定快照历史、重复sealed 409、未配置503；核对生成SDK真实二进制与旧资料普通解析一例兼容。相关Ruff/类型/契约/网页构建，已有15项领域和M0/旧大矩阵仅在实际改动影响时定向复测，不无条件重复。

源码候选和真实服务必须为同一准确SHA/指纹；准备、失败和最终证据分开，运行日志写runtime，再把静态快照列入不可变清单。证据只写自己 `others/reports/c1-public/t2/`，临时handoff在OS Temp；不覆盖T1或M0，区分候选环境与main。每轮相关代码本地commit，只暂存本包范围，不push。

两个里程碑可连续执行并各一次简报，无需等逐步回执。完成时交A最终完整SHA、许可锁/实际API origin/控制端能力/真实PG与runner/HTTP/SDK结果、静态清单/源码和产物来源、尚未验证事项及B2/D消费说明。A审查后才合main、备份兼容迁移/共享环境激活、更新一键入口与受影响三端并发布B2依赖；新公开基线未发布前B/C/D不启动下一模块。本包没有ECS部署、主库测试/重置/自动种子或新付费授权。

自查结论：C1已完成首次规划/手动启动，T1/领域PG接缝真实稳定，本包是原目标普通续办；新增表/重大预算变化或范围外文件再集中交A，不为局部接法重复整套Plan/Goal。所有未跑能力保持未验证。
