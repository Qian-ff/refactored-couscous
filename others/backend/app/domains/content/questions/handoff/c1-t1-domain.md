# C1 T1真实领域PG交接

2026-10-26，C / codex/c-content-ai-a2，D:/codex/worktree/ffb2/SafeLabPlatform。收到A批准的准确T1技术SHA db0ca18e5c0bf4fae1558755b702b7e4ddc2669a后，从清洁6719c31353a3bfa76a10e08820ea18eb0bad50e3普通合并，实际为fast-forward，保留原843/91bd与行锁修复历史。未cherry-pick重做，未推送。实际设置沿用Default/gpt-6.1-sol/medium；按该SHA的coordination、工作包模板、T1工作包及c1-public-handoff执行，无新Goal或Plan。

## 实际检查

共享backend/web/worker输入均匹配，未安装依赖。使用A指定的忽略管理配置，不复制或输出DSN/口令；root conftest仅用owner迁移授权，业务engine取runtime。共享pytest全局串行锁由既有shared_env入口持有。实际命令：

```powershell
. ./others/scripts/Use-ProjectEnvironment.ps1
$env:LABCONNECT_C02_TEST_ADMIN_CONFIG = 'D:/codex/worktree/0aed/SafeLabPlatform/others/runtime/c1-public/database-admin.json'
python others/scripts/shared_env.py backend pytest app/domains/content/questions/tests/pg app/domains/content/lessons/tests/pg -q --tb=short
```

独立只读runtime连接证实：实际数据库safelab_c1_test，头c1d0c000001；运行角色非superuser、非DB owner成员，public表所有者数量0。具体服务角色名及探针输出保存在忽略证据，不把私有连接写入仓库。没有使用主库、旧C02测试库或SQLite，没有跑A副公共schema测试。

## 结果及本轮改动

现有15项真实领域PG全部通过，没有失败用例。首轮输出5条Q/L授权查询笛卡尔积警告与1条既有TestClient弃用提示；未把警告直接忽略。

定位到C的version_query：已发布目标的read_resource_predicate仍带外层parent.creator_id，使B通用策略的内层catalog EXISTS引入无关父表。已发布读取不依赖草稿作者，故仅该发布分支改传literal(None)，源私有草稿分支及实际目标/学校/课程/审核/发布状态判断均保留，不修改B策略或公共文件。第二轮15项通过且笛卡尔积警告消失。

按A要求规范ready_batch终态夹具：明确input_sealed、真实格式文件键、合成execution_id、结果字节、停止确认、预留释放及retained计数。它仍是合成完成任务的领域夹具，不代表运行过真实上传/runner。15项复验通过；最终补齐文件键及合成执行ID后，仅相关test_imports.py两项再测通过，没有重复整个矩阵或放宽生产规则。

Ruff与diff检查通过。本轮只改questions/policy.py及tests/pg/test_imports.py，加本文与进度；不改迁移/公共配置/依赖、旧C02、worker、SDK或前端。无需重跑先前17项纯检查；没有失败修复循环或删除旧证据。

## 证据与边界

本树questions/test-results/c1/t1-domain（忽略区）：

- attempt1.log/exit：原始15 passed及笛卡尔积警告；保留。
- attempt2.log/exit：发布查询修正后15 passed。
- final.log/exit：导入终态标记与计数修正后15 passed。
- final-import-fixture.log/exit：最终夹具文件键/合成执行ID的两项定向复测通过。
- runtime-proof.py/json：仅runtime只读连接、真实数据库/角色权限/迁移头证明，不含DSN/口令。
- final-source.json：最终提交/工作树、实际命令与本轮源码hash（提交后生成）。

尚存1条共享环境的Starlette/httpx弃用提示，没有擅改依赖。15项中的semantic budget/admission只用于领域语义，不证明T2统一配额、队列、上传/导出实际任务、停止清理或32MiB工作峰值通过。XLSX实际依赖/往返、公共HTTP/真实SDK、B2/D2内容基线及运行器仍待A登记T2与实际验收；本次不是main接收、C1整包完成或B2放行。不自动启动C2/助手/监控，不空轮询未发布依赖。
