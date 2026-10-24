# C-02 公共接入工作包

编号 `c02-public-integration`，v2，2026-10-24由A主依用户v3 Goal启用。**状态：active；A提交生效委托并发送完整执行SHA后，A副实际开工。** 本包承接已手动启动的C-02全部后端/worker遗留，不重做既有设计；资料前端转D1，C只准备新题库/关卡。

## 输入、责任和启用

- A主：本包设计、必要裁决、main最终接收及技术基线发布；保持gpt-6.1-sol / max。
- 执行者：A副 / A-executor，host=local，thread=`01a16921-9ff8-7781-bdb8-6ede3d015d6c`，`D:/codex/worktree/0aed/SafeLabPlatform`，`codex/a-executor`。实际登记、清洁状态、gpt-6.1-sol / Default / medium须开工重新核验。
- main起点：`2f07bd08893f5f0b0e6260068b1c3e9106a7db68`。本工作包的发布提交另由A公布；启用时须给出完整执行基线SHA，不跟随移动main。
- C冻结候选：`ecb7129497d1f6a69daf09df6db3f2f30537d7ba`，业务基线`f516ef7abc66078325f103785c3c2e760441a56b`，contract 0.3.2，迁移`b1c0e0a00001`。
- 候选的完整说明通过`git show ecb7129497d1f6a69daf09df6db3f2f30537d7ba:others/backend/app/domains/content/handoff/c-02-integration.md`读取；同目录`c-02-accepted-addendum.md`、`c-02-guards.sql`及`others/ai_worker/content/README.md`共同作为输入。文件尚未进入main，不能把主树缺少该文件当成已合入。
- 先读[协作v3](../coordination.md)、[共享环境](../shared-environment.md)、[阶段](../a2-start.md)、[契约](../../contracts/README.md)、[Git流程](../git-workflow.md)和本包的[委托登记](../../contracts/execution-delegations.json)。C-02专项业务和真实验收保留；责任按v3转交，不再要求C回来进入M2。

本轮A将委托改为active并提交后发送准确SHA；执行者先同步该SHA核验委托和设置再实施。main仍0.3.2，公共实测通过后A发布技术基线给D真实联调；A副继续完成资料后端剩余修复和检查，不回交C。

## 自查、目标和边界

本包含必要的公共运行与数据变更，需A明确锁定执行边界。C的49文件候选仅完成领域实现及部分纯检查，真实PG、四格式依赖、HTTP和受限执行仍待验证；不得直接并入main或以能力布尔值冒称沙箱通过。

目标是完成原C02全部资料后端/worker遗留，并提供D1可真实联调的后台技术基线：八表兼容迁移/保护、私有存储、受限ParseRunner、lifespan、真实路由、0.4.0契约/SDK、可靠启动和证据。保留现有登录/课程与ASR；不开发资料UI、助手/监控/考试/原生新能力，不部署到ECS、不推送、不购买资源。

执行者仅修改委托allowed_paths。原C02冻结候选49个具体文件已逐项加入委托，允许A副接收、修复和测试；不再是receive-only，也不将遗留领域问题交回C。新增文件按既有公共白名单实施，确需范围外文件时交A先补具体委托。B核心模型只增加两项已说明的候选UNIQUE，不改B权限/业务。D入口、路由、设计资料和C原工作树保持原所有权。

## 1. 独立集成与候选环境

1. A副在登记独立树核验设置、main已提交的active委托、实际基线、暂存区及共享锁。保存已有工作后普通合并A给定SHA，再合并冻结C候选；不改写历史、不在main试接入。记录merge父级、冻结C文件blob及授权修复diff，区分原候选与继任修复；保留历史证据。
2. 静态审查候选模型、SQL保护、上传/恢复、授权及执行接缝，区分纯检查、跳过和未跑项目。涉及既有批准语义的重大不确定性先交A；不因风格重写已批准设计。
3. 业务依赖初始保持现有锁；控制端和API传输适配优先标准库，不将开发组httpx当生产依赖。解析四依赖固定为pypdf6.21.2、python-docx1.2.0、python-pptx1.0.2、lxml6.1.3，由A公共包解析完整传递锁、哈希和许可，禁止浮动安装。
4. main锁尚未接收时，不覆盖主树共享venv。使用本执行树忽略的`others/runtime/c02-public/envs/`创建候选验证环境，复用主树uv下载缓存；记录描述/锁指纹、解释器和本树源码位置。可新增本包专用验证helper；不得提供绕过任意工作树锁校验的通用开关。
5. worker锁为依赖唯一源；Docker内容镜像所需的仅解析依赖闭包从锁生成并校验，不复制ASR模型，不手工维护另一份漂移版本表。若新锁涉及业务环境，业务候选也使用独立验证环境。共享入口不能因锁不同而被静默降级。

完成条件：冻结源码及授权边界可追溯，候选环境与当前main环境明确分离；尚缺的实际检查不会被记为通过。

## 2. 数据库、迁移和运行角色

1. 以`b1c0e0a00001`为当前父头新增兼容迁移；注册C八表及实际模型。核心只补`uq_login_session_owner: login_session(id,user_id)`、`uq_course_content_parent: course(id,school_id,college_id,catalog_id)`；迁移前检查历史数据，不能删数据、重建旧ID或添加班级学院等于目录学院的限制。
2. 审查C的SQL候选后纳入Alembic，不把SQL文件当已执行安装器。验证循环FK的建表顺序和命名、NO ACTION/RESTRICT、延迟封存constraint trigger、成功版本/来源块/审核历史不可改、发布精确绑定及跨校/父级约束。downgrade顺序必须可在专用克隆库验证，禁止对演示/生产库试退。
3. 区分迁移所有者与API运行账号。运行账号不能为superuser、表所有者、可SET ROLE为所有者或可禁用触发器的角色；保留旧B业务所需DML和schema/function权限。迁移凭据单独保存在忽略的管理配置，不放入通用.env；现有shared_env会加载.env到业务环境，不能借此把owner凭据带给API。管理/迁移命令显式读取独立配置，生产API不挂载该文件；解析器和普通报告同样不得取得凭据。不得仅用同一owner账号证明保护有效。
4. 测试夹具用owner建立/升级专用本机测试库，业务/API与负向保护检查使用受限运行角色。保留既有串行测试锁；root conftest的迁移步骤不能在非owner下假成功，也不能让测试API继承owner连接。
5. 验证旧基线到新头、空库到新头、重复upgrade、核心行数/关联保持、运行角色拒绝禁用保护，以及完整上传封存/重解析事务的延迟约束。

完成条件：真实PG约束及权限证据齐备，旧功能回归通过；实际迁移ID随实现记录，不提前伪造。

## 3. 私有存储与上传恢复

A配置私有资料根、任务区和同卷锁命名空间；同一业务数据集的API使用同一物理文件卷，暂不支持各宿主独立目录或未经验证网络FS。原件不公开映射。实测hardlink封存、不覆盖、fsync、Windows LockFileEx/Linux flock及迟到写入恢复。

完整保留C-02及A补充裁决：真实I/O完成、句柄关闭和删除确认前保持预留/接收槽位；不能因lease、时间或PID变化清零。取得guard后才按持久状态/generation清理，锁文件不删除重建。任何成功版本或封存回指仍引用时不删原件。

预算保持：文件20MiB，TXT/知识点1MiB；账号1会话/全局2接收流；学校1GiB/公共1GiB/全局5GiB，计入原件、快照和残留；解析32MiB预留；实际可用磁盘扣预留后保底1GiB。所有私有配置只在忽略区，示例使用占位符。能力缺失准确503，不阻塞普通账号/课程。

完成条件：真实卷锁、并发预留/取消、崩溃清理和原件哈希保持均有证据，C现有纯测试不代替这些接入检查。

## 4. 受信控制端和ParseRunner

采用单部署受信控制端＋每任务隔离容器。控制端是固定模板执行器，持有Docker操作权限；API及解析容器均不持有Docker socket或宿主执行权限。控制端不加载业务.env、数据库/AI凭据；解析内容只交给隔离容器。禁止新增公开控制接口。

### 固定接缝

- API适配器实现C冻结的`ParseRunner`，注入`ContentRuntime(factory, storage, runner)`。factory每次新Session，配置缺失用UnavailableRunner语义，无普通进程降级。
- Linux使用文件权限受控的Unix socket；本机Windows只监听127.0.0.1，候选端口18767，冲突即停，不改Docker全局context、不开放公网端口。两者使用独立随机服务密钥，配置/密钥留忽略区；不使用用户JWT、API SECRET_KEY或云密钥。
- 私有协议为`labconnect.parse-control/1`：4字节大端长度＋最多16KiB JSON请求头；start输入为每帧不超过64KiB的长度前缀字节，0帧结束；认证通过后才读输入。操作仅capabilities/start/inspect/stop/result/release，控制JSON响应最多64KiB，result总量最多16MiB。严格校验UUID、格式、编码、输入哈希和所有长度；不能接收命令、宿主路径、镜像或挂载参数。
- `execution_id`预先持久化，同ID同任务/generation/版本/输入指纹幂等、异绑定拒绝。start返回前完整消费并校验本次输入，不留下继续消费迭代器的后台任务；源中断走停止/清理，不假成功。
- stop与实际启动串行，持久终止凭据在控制端重启和release后仍存在。release只清任务副本/临时数据，保留拒绝迟到start的凭据；永久原件/快照不归控制端删除。

### 执行与预算

控制端串行协调实际执行；用持久本地单实例锁与journal、固定execution_id容器名及安装实例标签恢复。恢复期间先核查/停止旧执行单元，无法确认则保持不可用，不能启动替代重任务。Docker不可用不能把“没查到”当停止。

容器基础Python3.13.16按官方digest锁定，运行镜像锁实际sha256 ID及来源SHA/内容指纹；不使用latest。非root、只读根、network none、cap_drop ALL、no-new-privileges，无API/DB/AI秘密、私有资料库或宿主socket挂载。仅本任务输出目录可写；内存总384MiB且不能用swap突破、CPU1核、pids64、tmpfs64MiB、解析60秒、stdout16MiB、stderr64KiB。日志不保存课件正文，不用无界Docker日志或capture_output收集。

为保持32MiB磁盘预留，输入流在受限容器的64MiB tmpfs内暂存，完整字节/哈希核验后才运行解析CLI；不再在宿主额外落20MiB输入副本。A固定包装入口只执行C CLI，输入封为只读；任务级输出最多16MiB写私有任务目录，结果不额外复制多份。API/数据库永久快照保持单独计量。若实际峰值不能满足该预算，先报A裁决，不静默扩大预留或漏算副本。

容器可先进入受限接收阶段；只有完整输入核验后才开始解析。这个内部暂存阶段不改变C的start消费完毕再返回、可取消和幂等契约。运行适配器须分别处理接收超时和解析60秒期限。

stop确认整个执行单元退出；release确认挂载、输出和临时区清理才返回true，重复幂等。用原IDinspect恢复丢失响应，不能生成新ID逃过旧任务屏障。源输入文件、正文和供应商秘密不进入控制日志。所有文件操作限于本安装实例的任务根，不按任意请求路径递归删除。

完成条件：真实Docker inspect与拒绝网络/其他文件/秘密访问、内存/输出/超时限制、先stop后start、控制端重启、release后迟到start及双API竞争证据通过。能力声明或mock不代替实跑。

## 5. 公共路由、生命周期和真实契约

在lifespan唯一挂接C scheduler，等待停止/清理路径；普通请求和文件流不持长DB事务。后台task factory绑定本树、当前运行角色和正确存储，测试显式隔离调度器及临时区，不能误扫演示文件。

挂载C实际router到`/api/v1`。contract目标0.4.0，在单一application.json中更新，再导出真实OpenAPI/hash和生成SDK；不提前改状态、不手写客户端。实际二进制PUT/download、Content-Length及UTF-8文件名正确。CORS暴露Content-Disposition/Content-Length，保留现有角色及来源限制。

网关只对准确的`PUT /api/v1/content/uploads/{UUID}/bytes`将上限设为22020096字节；业务仍20971520，其他路径维持既有2MB限制。先验证匹配规则，不能把整个/content都放大。公开云文档和DB端口继续关闭。

补真实本地`Open-C02-API.cmd`及对应启动脚本：按工作树端口启动/核验控制端和API，打开确实可用的开发API入口，说明D1资料UI尚未交付。保留旧启动器，不增加假的资料页面入口。缺配置、控制端停机时的错误和恢复真实可见。

## 6. 检查、接收和共享环境激活

证据根为执行树`others/reports/c02-public/`，包括完整SHA/树指纹、锁/镜像指纹、迁移/角色、API来源、每项命令stdout/stderr/退出码及实际缺项。报告脱敏；原件、配置、凭据和依赖环境不提交。

必要检查按以下顺序执行，命令在本包实现后必须确实存在：

1. `workflow.py status --baseline <A启用时公布完整SHA>`、shared_env status/probe，候选环境helper记录解释器与本树源码。A副前端5177、API8002；发现别人的服务不停止。
2. 候选worker解释器运行本树`content.verify --report <本树reports/c02-public/parser.json>`；四格式依赖缺失/跳过则本项失败。保留C的40项纯检查并增加公共适配器测试。
3. 在专用本机PG和共享串行锁下跑content领域、公共迁移/HTTP/受限运行角色及已有core/ASR相关回归；用`--tb=short`。现有测试入口迁移需owner而业务运行需非owner，先解决夹具隔离再跑，不能放宽角色骗通过。
4. Ruff、完整diff检查、真实contracts generate/check、pnpm check/build:web；SDK上传下载测试必须核对原始字节/哈希，不能只看HTTP200或JSON形状。
5. 本树真实8002 API来源核验及完整上传—提取—审核发布—有权预览下载、未授权/撤权/跨校/版本/并发/重启流程。审查候选9项PG只作为起点，缺少的关键场景由A副补在受托候选领域测试或公共测试，不回交C收尾。
6. 真实沙箱、两个API/runner竞争、同卷锁与丢失响应/迟到start/清理故障；普通课程/健康请求在重任务或控制端失败时仍可用。
7. 候选全部必要检查通过才交A接收，A副不自行merge main或发布基线。技术接入不表示C-02整包/UI或B2完成。
8. A接收后，依A后续明确续办同步完整main SHA，再激活已接收锁对应的主树共享环境；不能在候选阶段覆盖。若服务占用文件或需停止非本人进程，先报告A协调。正常共享入口随后核验锁/本树源码及ASR仍可用，不把候选环境冒称共享环境。
9. 合入后按真实main源码重建受影响的网页/Windows/Android现有客户端，记录源码/contract与产物；只验证已有功能兼容，不冒称资料UI、原生资料保存或A2完成。执行本轮真实API入口，保留旧一键入口。
10. A主确认后公布给D完整技术SHA、contract/migration、运行配置、API来源和验证边界，供D1真实联调；C只读消费后续领域依赖，不再接回资料遗留。正式ECS部署及云端实际卷/备份恢复另由A安排，当前云仍是旧版；不得将本地Docker沙箱证据写成云端上线通过。

不得使用真实学校数据、私密PPT、收费AI或新增付费云资源。下载仅官方锁定依赖/镜像并记录许可。网络或环境不具备就准确记录阻塞，普通局部失败最多三轮；不能换成普通子进程、SQLite业务库、公开Docker服务或无权限执行绕过。

## 提交、里程碑和下一责任

执行后每轮仅提交本包实际允许路径；用`workflow.py checkpoint --executor A-executor --package c02-public-integration --baseline <A公布SHA> --paths <逐项相关文件>`。C候选的接收merge保留历史；原候选blob与A副受托修复diff分别记录，修复仅限委托列举文件。委托、ownership、main发布及阶段导航由A主维护。

按“独立树公共接入完成＋真实证据”集中交A一次；关键阻塞及时报告，普通进度不逐命令汇报。A接收及合入后复查可在同一已授权包续办，不拆零碎审批包。候选不完整可明确WIP，但不得合入main充当完成。

任务结束/停工/换聊按handoff写系统临时目录，引用本包和证据，一次摘要/绝对路径交A。临时文件跨环境不可见时，已提交接入说明仍是完整依据，不要求用户寻找本机文件。

当前下一责任是A副1接收生效SHA后实施，D1并行准备资料前端。A副交A真实后台候选，A发布技术基线供D1完成联调；A副复验合并源码，A在资料前后端均通过后登记原C-02完成。C只准备新C1，不再执行旧M2/M3；B2按具体内容基线、助手/原生/监控按后续阶段放行，checkpoint-2仍需实际集成验收。
