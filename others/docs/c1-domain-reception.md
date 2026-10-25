# C1 T1与真实领域PG接收

2026-10-26，A接收 `46394d57fc077e381748acb306e133476a47e7fe` 为 [T2公共接入](ai/c1-runtime-public-integration.md) 的冻结输入；**尚未把C1代码/迁移合入main，尚未发布C1 HTTP/SDK、运行器或B2基线。** 现行main仍0.4.1/迁移 `c02d0c00001`，可运行资料页的实际版本见[主线接收](material-ui-main-reception.md)。

## T1技术与修复

A副在 `codex/a-executor` 交T1技术SHA `db0ca18e5c0bf4fae1558755b702b7e4ddc2669a`：原样接C领域、登记23表、静态迁移 `c1d0c000001`、专用 `safelab_c1_test` 与非owner入口。只修改模型注册、新迁移、公共schema检查、数据库管理profile和交接5个公共文件，没有把C1路由/SDK/runner或新依赖写入main。

A复审指出并已修复两类实际问题：C的QuestionDraft/LessonDraft需按question_id/lesson_id行锁，6处不能传给固定model.id的旧helper；固定Q/L版本即使无内容变化UPDATE也必须保持封存，不能刷新xmin后重新追加来源。C行锁补丁 `6719c31353a3bfa76a10e08820ea18eb0bad50e3` 已原样进入最终T1；数据库回归实际验证no-op拒绝、xmin保持与后续子行仍拒绝，保留合法创建事务补齐和草稿修改。

T1专库公共检查1项通过，含兼容升级/重复升级/专库退回再升、旧行摘要、非owner、跨真实提交固定版本/子记录、草稿台账与审核发布。候选相对d4a的差异检查通过；旧失败/通过记录保留。A已核对新3个附件及4个源码hash（行尾规范化后与Git内容一致），清单 `9f8e2f3ecb1ad2b72d556a418897bc1023c842c014a6b1594791166adcb5e60c`；旧6附件清单仍 `d1dfe630c6953722bb1a573fef2c52c34b9f278ec3661427b3b6521b3e63f4d5`。记录位于A副树 `others/reports/c1-public/t1/` 及 `revision-1/`，A回执在本机 `others/reports/c1-t1-receipt/receipt.json`。

## C实际领域PG

C在 `codex/c-content-ai-a2` 从干净671快进合入准确db0ca，使用A发出的私有管理配置及既有shared_env串行锁，仅在 `safelab_c1_test` 执行两域15项真实PG。runtime只读证明非superuser、非DB owner成员、public表所有者0，实际头 `c1d0c000001`；未用主库、旧C02验收库或SQLite，未输出/复制管理凭据。

15项全部通过。C随后收尾发布查询的外层作者列：仅已发布分支改传 `literal(None)`，消除内层catalog EXISTS笛卡尔积，保留源私有草稿作者及学校/学院/课程/审核发布过滤；没有改B策略。导入完成态夹具补正确blob键、合成execution_id、sealed/停止确认、结果与retained计数、预留0，不放宽生产规则，也不声称合成终态证明runner成功。

A已读最终4文件差异、真实15通过日志、最后夹具2项定向通过、4个exit=0、runtime证明及两个最终源码hash；最终候选463干净且包含准确db0ca。只有既有Starlette/httpx弃用提示，未为此更换依赖。原15项最终功能结果与最后受影响2项复测分别记载，没有把旧日志改为新全矩阵重跑。

详细交接在C候选 `others/backend/app/domains/content/questions/handoff/c1-t1-domain.md`；原始日志/exit/源码与runtime证明在同模块忽略的 `test-results/c1/t1-domain/`。此前91bd/843/671和失败/警告历史保留。semantic budget/admission只证明领域语义，不证明统一计量、队列或真实导入导出执行。

## 下一步

A副按active [T2工作包](ai/c1-runtime-public-integration.md)接收463，在独立候选环境接CSV/XLSX、双向计量/队列、固定CLI与真实HTTP/0.5.0 SDK；[临时接缝登记](../contracts/integration-handoffs.json)列明四个C1接缝及对应测试串行交A副，C不并行编辑。其余C领域模型/服务/夹具保持冻结，新增缺陷仍由A协调责任方。

A接收T2后再合main、兼容迁移/激活与受影响客户端验收，发布固定版本、学生安全DTO及受控答案服务，B2/D2才接实际基线；C2/助手/监控、新原生能力的首次门禁不因本次续办而自动放行。当前无必须用户另选的业务问题，不要求Daybreak或付费服务。
