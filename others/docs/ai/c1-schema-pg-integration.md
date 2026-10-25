# C1 T1：模型、迁移与真实领域 PG 入口

编号 `c1-schema-pg-integration`。2026-10-26，A主对已由用户手动启动的C1作普通公共接入续办；不是新模块首启，也不是C1整包验收。仅本文件与main已提交的active委托、A实际发送的完整执行SHA共同生效。

本包现已完成技术与15项领域PG接棒，结果见[接收记录](../c1-domain-reception.md)；当前具体实施委托转[T2](c1-runtime-public-integration.md)。下文保留原T1范围和执行条件，不重复启动或重跑。

## 执行者、输入与边界

- A副 / A-executor，host=local，thread=`01a16921-9ff8-7781-bdb8-6ede3d015d6c`，登记树 `D:/codex/worktree/0aed/SafeLabPlatform`、分支 `codex/a-executor`。gpt-6.1-sol / medium / Default；先核对实际设置、树、分支、暂存区、委托及共享环境。
- 先读[统一规范](../coordination.md)、[工作包模板](work-package-template.md)、[共享环境](../shared-environment.md)、[契约](../../contracts/README.md)、[Git流程](../git-workflow.md)及[首版路线](../delivery-workflow.md)。
- 起点main `cff0d654b1801671fba453dd728c0ba3d3a4e3c4`；实际开工必须再包含A消息的完整发布SHA。现行契约0.4.1，迁移 `c02d0c00001`。
- C最新领域候选 `84355fecf0ddb0edb1dc9bcfd030c2f8ee7cd695`；保留 `91bd07d068bec252da596d1ac390b7a1c75c15ae` 历史。候选 `questions/handoff/c1-m1-handoff.md`、`c1-plan.md`、`c1-progress.md`、`c1-http-candidate.md` 为需求输入，旧14项PG文字以新增接收槽回归后的15项为准。
- 上述路径均位于 `others/backend/app/domains/content/`。两个新域只原样接收，不借本包接手C领域修复；C待T1后维护这两域，A副维护登记的公共文件。存在多个merge-base，核对实际合并树及新域文件blob，保留已接收C02、检索0.4.1及其修复。
- 私有只读草案 `C:/Users/lenovo/AppData/Local/Temp/LabConnect-C1-integration-readonly-20261025.md` 可作说明，不是权限来源；其中依赖、runner、HTTP/SDK及原生建议均留后续包。

本包先提供23表、必要数据库完整性和专用非owner PG技术SHA，使C可跑15项领域PG，解除“没表却先要求PG通过”的循环。固定题目/关卡的正式公共发布仍由A后续接收。T1不改公共API版本、路由、SDK、worker、队列、旧C02领域、前端、原生或ECS，不推送，不发布演示种子。

## 1. 接收与兼容迁移

在自己干净树保留历史后普通合并A发布SHA及C准确候选。登记 `questions.models` 的11表与 `lessons.models` 的12表；只新增 `c1d0c000001_questions_lessons.py` 静态Alembic迁移，父头为实际 `c02d0c00001`。不导入可变领域模型执行DDL，不改既有迁移，不用create_all冒充迁移。

保留现有组织/账号/课程/资料ID与行；FK、复合审核绑定、有序导出唯一性、NULLS NOT DISTINCT来源去重按候选模型落地。downgrade只在本包专库检查，禁止对主库或已有C02验收库试退。新增23张表的具体结构以C冻结模型为准，不另造学习/考试表。

## 2. 必要数据库完整性

沿用C1既定规则，以普通业务场景验证：
- 固定QuestionVersion、LessonVersion、SceneAsset不可更新或删除；固定source/question/origin子行在创建事务内可补齐，提交后不可追加、改删。检查必须跨真实提交，不能只用savepoint证明。
- 主对象所属库、creator、固定版本对应关系稳定；revision/retired等合法生命周期更新可用。审核版本/目标/提交者/声明绑定不漂移，submitted仅一次决定；发布精确绑定已批准审核，退用保持历史。
- 草稿来源和当前题目引用允许正常替换；LessonDraftQuestionOrigin保留追加来源，解除活动引用不能清台账；整份草稿丢弃允许同一事务先删来源再删父草稿。必要时延迟到事务结束核对，避免保护误伤合法操作。
- 已授权公共版本跨校独立复制可保留原私有来源FK作为许可历史；这不授予原件读取。不能一律加同校来源FK误拦合法复制，不新增学院相等限制。
- 候选任务/batch的持久绑定保持原语义；T1不预建runner状态机，不为尚无T2的流程伪造成功或放宽保护。

尽量复用现有PG约束/小型trigger方式，不引入通用历史框架。确需修改C领域模型、服务或夹具时，先交A/C具体问题，由C在自己的树修复；A副不以旧测试为由削弱保护。

## 3. 专用测试库与配置

只管理本机白名单专库 `safelab_c1_test`；原 `safelab`、`safelab_c02_test` 和共享PG容器/服务保持。复用现有迁移owner/运行配置分离、共享pytest串行锁，管理凭据留A副忽略的 `others/runtime/c1-public/`。业务仅取得非owner runtime配置，报告脱敏。

在 `others/deploy/content/database.py` 最小扩展显式C1测试profile，固定库名、配置目录和受限角色；保留既有C02入口默认行为。复用现有独立owner管理配置，不能假设现在通用.env仍是owner、把owner放回.env或让API继承管理配置。不得增加可指定任意库/任意路径的绕过选项。读取现有管理配置时核验其所属本项目本机实例；不输出DSN、密码或密钥。

现有 `LABCONNECT_C02_TEST_ADMIN_CONFIG` 历史名可继续复用。根conftest仅在实际需要时最小适配专库，维持owner迁移、runtime业务及原测试锁。专库runtime不能是superuser、所有者、owner成员或能禁用保护的角色。

T1保持backend/worker描述、锁、共享venv与解析运行器原样。当前15项PG依赖现有CSV/模型闭包；XLSX实际往返和缺失解析依赖留T2统一登记。若实际发现T1导入即缺依赖，先交确切模块/错误和最小依赖范围给A，不私装共享环境。

## 4. 本阶段完成与交接

只跑本次相关的正常检查：
1. 专库从旧头到新头、空库到新头、重复upgrade，旧表数据摘要/ID保持；必要的专库downgrade再upgrade可复现。
2. 非owner正常DML、固定快照跨提交保护、草稿正常替换/整份丢弃、审核发布绑定和合法公共复制，保留C02原有保护；不追加高级安全/压力/复杂故障矩阵。
3. 业务依赖指纹不变、相关Ruff和diff检查；只要足以证明本次迁移及入口，不重跑已有全仓/三端/解析器完整矩阵。

以候选完整SHA交A，包含模型/表数、新迁移头、owner与runtime分离的脱敏证据、确切PG命令和本机私有配置绝对路径、所有真实通过/未跑项；证据写自己 `others/reports/c1-public/t1/`，文档写 `others/docs/c1-public-handoff.md`，handoff放OS临时目录。每轮源码修改本地commit，范围仅active委托。

A复核后将准确T1技术SHA及私有非owner入口交C。C合并该技术SHA，在共享测试锁下执行15项领域PG并修复自己的领域/夹具；纯SEMANTIC_BUDGET夹具不是T2真实统一配额或runner证据。A副不提前替C跑全部领域或改其源码。后续T2由A另登精确包，包含依赖/计量/固定任务运行/HTTP/SDK，届时才准备B2依赖发布。T1不启动B2、C2、D2、助手、监控或新原生能力。

自查结论：本包是已授权C1的公共接入子阶段，无新增业务选择；明确划开T1与T2，具备授权后实施条件。若专库权限或既定完整性存在实际矛盾，集中交A裁决，保留数据与可运行主线。
