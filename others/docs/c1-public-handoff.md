# C1 T1：公共表与专用 PG 技术交接

## T2运行/公共接口候选（0.5.0，尚待A接收）

本分支已普通合入A规则 `c22328671a5d32715c4b5dbc10b66d5f4d46aa84` 与最终C领域 `46394d57fc077e381748acb306e133476a47e7fe`。仅四个C1接缝及对应测试由A副串行扩展，其他领域/T1迁移原样接收。先保存WIP `4505e6f`，其本身不是验收通过；后续准确候选SHA、最终检查、许可和静态证据以 `others/reports/c1-public/t2/manifest.json` 为准，不能拿旧WIP来源冒充最终服务。

实现范围：真实request级磁盘采样/ContentBudget/TransferAdmission/TransferIO；双向旧资料+C1存量与队列、接收槽、单重任务/恢复/停止屏障；固定三类控制协议及sealed fd CLI；CSV/XLSX真实预检、原子确认草稿、教师审核发布、有序固定版本导出/重授权Blob；真实staff路由、0.5.0 OpenAPI/生成SDK、B2内部快照及安全学生DTO。旧材料TS类型名由生成规则兼容，未改D产品入口/页面。候选不自动发布60题/六关或演示种子到main。

候选环境只有本树runtime/c1-public，API生产不导入Excel解析库，测试dev与worker固定依赖和许可在锁/manifest。受信镜像包含纯CLI闭包，无数据库、API配置、dotenv、SQLModel或语音模型。控制端18768与main18767分开；新协议显式核对三任务，C1 30秒、资料60秒，继续无网络/nonroot/只读、384MiB/CPU1/pids64。实际回执记录内核seals=15、输入hash/字节及/work实际44MiB；受信子进程只用/work作临时目录，密封输入最多20MiB，总临时64MiB。普通导出文件和控制端输出共存仍在32MiB工作预留内；未宣称验证压力峰值。

可执行入口（仅A副活动包）：

```powershell
python others/scripts/c1_candidate_env.py prepare --surface backend
python others/scripts/c1_candidate_env.py prepare --surface worker
others/runtime/c1-public/envs/worker/Scripts/python.exe others/deploy/content/prepare.py --profile c1
others/runtime/c1-public/envs/backend/Scripts/python.exe others/deploy/content/database.py prepare-c1-test --primary D:/SafeLabPlatform --admin-config D:/codex/worktree/0aed/SafeLabPlatform/others/runtime/c1-public/database-admin.json
```

控制端使用同目录control.json，API使用api-runtime.json（仅runtime连接/应用secret/内容配置/合成测试口令，不给API owner配置），首次专库需明确`api.py --profile c1 --config <固定api-runtime绝对路径> --seed-test`；已有样本则不重复seed。运行日志只写runtime/logs，封存后才入reports。配置均忽略且不输出密钥。main仍c223/0.4.1/c02d0c00001，未合入C1/迁移/改共享依赖。

实际检查分开记录：小型协议/混合接收与额度、真实CSV/XLSX往返和一次实际取消/重试/停止清理、旧资料兼容一例、真实staff HTTP与学生/跨校/学院/未任教课程拒绝、B2私有固定快照/安全投影/私有SVG、SDK原始字节/Blob、503、相关Ruff/类型/契约/网页构建。最终记录必须对应当时准确源码/指纹；初次网络/输入cursor失败保留，不改写为通过，也不重跑C15或M0/客户端矩阵。

B2继续使用questions.assessment.resolve_assessment_questions和lessons.assessment.resolve_lesson_publication，持久化自己的评分/素材快照；StudentLesson生成类型来自真实教师预览模型。student_lesson_from_snapshot只过滤当前来源和私有评分，真实任务/关系/解锁由B2后续判定。学生不能调用教师预览/直接取得SVG，无新增学生答案接口或裸asset/hash链接。D后续消费生成DTO和接口，由D独写入口/编辑器，不由本包实现D2。

A接收后另行安排main备份/兼容迁移、共享环境激活、一键入口与受影响三端发布。本候选不等于这些动作、B2/C2/D2首启、原生保存、真机/G/ECS验收；旧T1段落保留历史原义，C15已由C实测并被A接收，未在本轮再次全跑。

2026-10-26，A副 / `codex/a-executor`，按已登记 `c1-schema-pg-integration` 实施。输入 main `d4a328bb0fb9742d3d981c20c68f7cff3be5fa3a`、C 候选 `84355fecf0ddb0edb1dc9bcfd030c2f8ee7cd695`，随后原样普通合并 A 明确批准的 C 修复 `6719c31353a3bfa76a10e08820ea18eb0bad50e3`；两段历史均保留，两个新域逐路径 blob 与最新 671 候选一致。准确技术 SHA 以本轮提交及 A 发送记录为准。

## A 复审后的同包返修

初版 `b139213a4a5a9e2e6bb0f1ce528b0382b141de54` 与其 `t1/manifest.json` 保留，不改写旧结果。A 指出固定 Q/L 版本的 no-op UPDATE 即使内容未变也会生成新 xmin，可能重新打开子记录插入：现已在相等内容快捷返回之前，无条件拒绝这两类父版本的 UPDATE。未使用 `RETURN OLD` 冒充阻止新 tuple，也没有改变正常创建事务补齐、草稿更新或 C 领域语义。

现有一个真实公共检查增加已提交 Q/L 版本 no-op UPDATE 拒绝、xmin 保持及同事务内后续子记录仍被 `C1_SNAPSHOT_CLOSED` 拒绝的回归。最终本轮 **1 passed**，新证据位于 `others/reports/c1-public/t1/revision-1/`，原 schema/pytest/失败记录不覆盖。另清理静态 DDL 行尾空白；差异检查以 `git diff --check d4a328bb0fb9742d3d981c20c68f7cff3be5fa3a <最终技术SHA>` 为准。初版只检查工作区差异，不能作为发布祖先到 b139 的检查通过证据，已在此纠正。

## 本阶段已交付

- `app/models.py` 登记 Q 11 表、L/场景 12 表。新静态迁移 `c1d0c000001_questions_lessons.py`，父头 `c02d0c00001`；DDL/索引固定在迁移内，执行迁移不导入可变领域模型。保留复合审核绑定、会话所有者 FK、NULLS NOT DISTINCT 来源去重、有序导出唯一性和原 C02 约束。
- 小型 PG trigger 固定版本/场景及固定子记录；固定子记录仅可在父版本创建事务内补齐，提交后关闭。通过可见父行的事务状态判断，包含 savepoint，并将 xmin 恢复为当前 epoch 的 xid8；未新增领域字段/通用历史框架。主对象身份、审核绑定及已决定状态不漂移，发布必须对应已批准审核，发布后只允许退用。
- 草稿来源和当前题目引用仍可正常替换。草稿题目来源台账的删除校验延迟至事务最终状态：只移除活动不能清台账，整份草稿丢弃可先删台账再删父草稿。固定来源不增加一刀切同校限制，跨校复制谱系和历史私有来源 FK 可保留；这不赋予原件读取权。
- `database.py prepare-c1-test` 增加固定白名单 profile：仅本机 `safelab_c1_test`，仅本树忽略目录 `others/runtime/c1-public/database-admin.json`。读取既有独立管理配置并核对与本项目业务实例的 host/port/database 一致；不假设业务 `.env` 是 owner。运行角色与 owner 分开，保留 C02 原入口默认行为。

本包没有改 C 领域文件、旧 C02 顶层、root conftest、依赖描述/锁、共享环境、HTTP 路由、SDK、worker/队列、前端、原生、API 版本或 main 数据库。专库实际头为 `c1d0c000001`；正式 main 保持 A 冻结源码、0.4.1 / `c02d0c00001`。不代表 C1 公共发布、B2 放行或整包完成。

## 已执行的公共检查

`tests/test_c1_schema.py` 为一个真实 PostgreSQL 公共检查，不依赖外层 fixture savepoint证明不可变性：

1. 专库空 schema 到新头；C02 有合成组织、库、资料原文后升级，全部旧表行数/摘要及 ID 保留；重复 upgrade、仅专库 C1→C02 downgrade→upgrade。旧 B1 有意禁止历史降级，因此空库检查只在白名单专库重建 public schema，不修改既有 B1 迁移或对主库降级。
2. 实际 runtime 不是 superuser、DB/table owner、owner 成员，不能建 schema 对象；正常 DML 可用。固定版本/场景更新删除、固定子记录提交后追加/删除被拒，父绑定稳定，原 C02 原文保护仍在。
3. 草稿来源替换、活动解关联、来源台账单独删除拒绝及整稿丢弃通过。Q/L submitted 审核不能提前发布，批准后可正常发布/退用，审核历史绑定保持。跨校谱系/来源 FK 保留通过；这是 schema 兼容检查，未替代服务端授权判定。

最终结果 **1 passed**；Ruff、diff 检查通过，共享 backend/web/worker 输入与主树一致。没有为 XLSX 安装依赖。既有 Starlette/httpx 弃用提示保留，不修改共享依赖。证据在本树 `others/reports/c1-public/t1/`，失败尝试与最终成功分开保留，未复跑旧全仓/解析器/三端矩阵。

测试结束专库清为 pristine 新头，C 不会继承本次检查的幂等回执。只有本专库使用合成 seed；主 `safelab`、旧 `safelab_c02_test`、主线运行器和正式原数据未改。

## C 的确切接棒方式

A 复核后向 C 发送完整 T1 技术 SHA，C 普通合并该 SHA，再在自己树执行。私有配置实际绝对路径：

`D:/codex/worktree/0aed/SafeLabPlatform/others/runtime/c1-public/database-admin.json`

它由测试管理入口持有 owner/runtime 两条连接；领域业务 engine 只取非 owner runtime，owner 仅由 conftest 作迁移/授权，不把管理凭据写回 `.env`、日志或仓库。复用历史环境变量名和共享 pytest 串行锁，无需本轮改 root conftest。

```powershell
. ./others/scripts/Use-ProjectEnvironment.ps1
$env:LABCONNECT_C02_TEST_ADMIN_CONFIG = 'D:/codex/worktree/0aed/SafeLabPlatform/others/runtime/c1-public/database-admin.json'
python others/scripts/shared_env.py backend pytest app/domains/content/questions/tests/pg app/domains/content/lessons/tests/pg -q --tb=short
```

目标是最新 **15 项**领域 PG，尚未由 A副代跑。不要按旧 91bd 候选/14 项计算，也不要让它使用演示库或普通 owner `.env`。C 的 semantic budget/admission 夹具只证明领域语义，不是 T2 统一配额/runner 证据。

## 已发现并收到 C 修复的问题

公共检查曾额外尝试正常 `create_question → submit_question`：创建成功，提交在 C `questions/services.py` 的 `locked(db, QuestionDraft, question_id)` 抛 `AttributeError: id`。既有 `content/services.py:locked` 使用 `model.id`，而 `QuestionDraft` 主键为 `question_id`，`LessonDraft` 为 `lesson_id`。证据 `pytest-attempt2-domain-defect.log` 保留。C 在 671 修复中新增按 `DOMAINS.parent_key` 的 `locked_draft`，保留 `FOR UPDATE`、`populate_existing` 和无权限/缺失拒绝，替换两个域六处调用；C 报告 17 项纯检查通过，A 已审查批准，A副仅原样合并、未改 C 文件。本次未替 C 跑 15 项领域 PG，待合入准确最终技术 SHA 后由 C 执行；最终公共测试仍仅证明数据库合同，不将旧命令失败改称领域通过。

此缺陷不妨碍交付可运行迁移和专库入口，正是 T1→C 真实 PG 阶段需要处理的内容。CLI sealed 输入适配、CSV/XLSX依赖/计量、固定任务运行、路由/SDK和真实发布留 T2；助手/监控/原生新能力、云端与 G 独立验收未放行。
