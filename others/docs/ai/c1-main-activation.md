# C1 主线接入：先完成启动工具，再激活与构建

编号 `c1-main-activation`。2026-10-26由A主登记，承接已验收的T2候选 `b7b27c72c1fdfccd434663f2fc683b5576202967`。是已首启C1的普通集成续办，gpt-6.1-sol / medium / Default，不新开Goal或重复Plan。

## 身份、来源及门禁

A副 / A-executor，host=local，thread `01a16921-9ff8-7781-bdb8-6ede3d015d6c`，登记树 `D:/codex/worktree/0aed/SafeLabPlatform`、分支 `codex/a-executor`。先读[协作规范](../coordination.md)、[工作包模板](work-package-template.md)、[共享环境](../shared-environment.md)、[当前主线接收](../c1-main-reception.md)、[T2目标](c1-runtime-public-integration.md)、[Git流程](../git-workflow.md)及具体委托。

本包初始main代码仍 `c22328671a5d32715c4b5dbc10b66d5f4d46aa84`、0.4.1/c02d0c00001；先包含A实际发送的本包规则发布SHA。在A副树合并准确规则SHA，保留b7/79/463/db0ca等历史。T2运行器、CLI、路由、DTO、迁移及锁不再重做；P1只补准确的main启动/准备接缝。A收到P1后才把T2与工具一起合main。

**当前只放行P1。P2必须等A实际接收P1/T2并发送完整main执行SHA。** 分支职责不变：A副只在自己分支改源码；对main只执行P2明确的忽略配置/依赖/运行/构建操作，不直接编辑受跟踪源码。

## P1：主线准备与演示入口

1. 复用现有prepare.py、Prepare/Start/Stop/Verify-ContentParser、Start-Backend、Start-A1，不建第二套环境管理器。现在prepare.py仅支持A副的c02/c1候选profile，旧Prepare脚本硬编码候选venv；增加最小的严格primary-main准备路径，用主树共享worker/实际锁和纯14包闭包，输出固定忽略目录 `others/runtime/content-parser/`、本机18767。候选18768/profile/角色硬校验保持，不放开任意目录/主机/命令或helper旁路。
2. main准备程序必须核对自己是真实primary/main、安装版本与已接收锁一致；复用已校验wheel/uv缓存，继续核对来源/hash/许可。构建与配置只写忽略区；不得在运行main准备时重写受跟踪的许可/manifest/源码。许可与已接收清单不一致时报告差异，由分支修复/A接收，不在main悄悄生成补丁。
3. 为实际v1→v2切换保留原控制实例/key/journal和停止屏障，确认原执行已停止/released后再换image/协议；不复制候选测试库、账户口令或任务状态。无法确认旧执行停止则保留并报A。必要的旧journal/探针兼容只在本包明确的control/runner/probe范围最小修正，不扩任务类型或降低保护。
4. database.py升级输出须报告实际新迁移头，不能因main管理profile不是c1-test而仍硬编码打印c02头；owner/runtime分离及本机测试库白名单不放宽。
5. 新增 `Open-C1-API.cmd` / `others/scripts/Start-C1.ps1` 作为main本轮API演示入口，复用既有主线启动逻辑，支持 `-NoOpen`；正常打开实际8000/docs，提示网页资料仍用Open-Materials。不创建假题库/学习UI，不改D入口。旧Web/Windows/Android/资料入口保留。
6. 只做相关脚本解析/最小profile行为、Ruff/diff等静态工具检查；必要的小型QA写登记文件。无需重复T2 M1/M2、15领域PG或三端构建。实际main新profile运行留P2，不用候选库冒充main验证。

P1完成：本地commit，交A具体完整SHA、改动及检查、未跑的main动作和临时handoff。保留干净分支。此后停在P2门禁，不能凭本包active自行迁移main。

## P2：A发实际main SHA后执行

1. main原库、配置与任务
   - 核对原PG容器/卷、实际main库、非owner API配置和独立迁移owner；迁移前可恢复备份及hash，记录原表/ID/内容摘要。保留真实原库、账号/课程/资料/历史，禁止重建、reset或重新seed原库，不用测试库替代。
   - 只启停经PID/启动时间/命令/树/配置核对的本项目main API/Web/控制端；不按进程名全杀，不停其他树服务，不改Docker全局设置。原ASR18765、模型缓存和已验证版本保持。
2. 共享环境与协议
   - 按已接收精确锁激活原有backend与worker两套共享venv，复用缓存和原解释器；不复制候选venv，不建第三套正式环境，不升级既有ASR/解析版本。只在A明确main SHA对应锁上执行。
   - 从实际main准备受限image/纯CLI闭包与私有18767控制端，保留原控制历史/凭据及确认清理，客户端与服务端统一labconnect.content-control/2。候选8002/18768保持分离；未核验不占用替换别的服务。
   - 新23表按已接收c1d0c000001兼容迁移，并为原非owner运行角色授必要DML/函数权限；owner不进应用.env/API/worker。先核对原表摘要保持，再开始本轮合成验证。主库不执行领域pytest、schema重建或downgrade。
3. 实际main普通流程
   - health/identity/OpenAPI精确对应A给的main SHA、0.5.0/c1d0c000001；C1实际能力和旧资料读取/解析可用。实测新入口及旧资料入口。
   - 一条普通旧资料兼容，加一组明确标注“研发合成验证”的题目/关卡创建—审核发布—固定版本/受控私有快照/学生安全投影，以及一例真实CSV流转/下载摘要即可；候选XLSX及完整权限矩阵已有证据，不无条件重跑。
   - 保存可移交的固定版本/发布/课程ID、hash及实际服务说明供B2消费，验证身份/权限的范围准确。合成样例不是专业安全内容已获人工审核的声明；不得自动发布专业60题/六关或把原草稿seed到主库。
4. 一键入口与产物
   - 若实际运行发现需源码修复，先在自己分支提交交A，等A接收并给新的final main SHA，再做最终客户端构建；不得直接改main或让旧产物冒充新源码。
   - 从最终main重建受影响Web生产、Windows、Android debug一次，记录源码/指纹/契约/产物hash，三端实际登录到已有资料页及基本访问。当前尚无题库编辑/考试页，不假称这些UI通过；安卓模拟器/真机分开。
   - Windows/安卓持久保存、完整录音/TTS/助手、九组合及G独立验收仍未因此完成；不追加新原生能力或高级压力矩阵。

P2证据单独写 `others/reports/c1-public/post-main/`，运行日志先写runtime再封存快照，不覆盖M0/T1/T2。生成操作不得修改受跟踪main文件；发现差异先说明并保留，不强制重置。提交/汇报准确来源、备份/旧数据、角色/迁移/能力、固定样例ID、实际检查与产物、失败和未测项；源码无变化不空提交。

## 接收与后续

A最终确认真实main与产物后才发布固定内容版本、学生安全DTO与受控答案服务的B2/D2依赖SHA。B2/C2/D2仍按新模块首次手动启动规则，不因本包自动开工；C02原生保存与G等边界保留。不得推送、ECS更新、购买新资源或使用Daybreak；本包不是全项目完成。

自查：这是已批准C1候选的必要启动/运行集成，无新的业务或用户界面选择。保留版本/原库/角色边界，普通局部问题自主处理；未知旧执行、实际预算或范围外源码问题集中交A，不反复询问已有恢复授权。
