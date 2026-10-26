# C1候选接收与主线激活准备

2026-10-26，A已核对并接受T2候选 `b7b27c72c1fdfccd434663f2fc683b5576202967`，**当前main尚未合入C1代码，运行仍为c223/0.4.1/c02d0c00001。** 先由A副按[具体包P1](ai/c1-main-activation.md)补主线启动/准备接缝，A接收后再将T2与工具一起合入并放行P2迁移/激活/构建；不把候选服务当作主线。

## 接收依据

- 实际候选API8002来源b7、0.5.0/c1d0c000001，与私有18768及image、网页产物分别有准确记录。A实际GET identity/health及OpenAPI；规范化OpenAPI与提交字节一致，SHA256 `656462a90a893433a4841a9516f5145d19c1dfed0f8581969affbb1ca839d5f4`。
- 不可变清单 `others/reports/c1-public/t2/manifest.json` 在A副树，hash `70c8a9e073bac30511da2c2e479e3ecceb29a076153e0c27c2fb423260d9dc76`；A核对17附件、7个来源文件hash全部匹配。原M1六附件及此前T1/C领域证据保留。
- 结果按源码区分：79c6后端14项＋15子检查；0cf实际公共HTTP/runner/PG两项；最终b7工具选择QA、契约/类型/构建及生成SDK浏览器一项。0cf→b7的backend/app与web/src实际无差异；没有把旧M1改称新全矩阵重跑。
- 实际CSV/XLSX导入预检—确认草稿—审核发布—固定导出往返、运行中取消/停止清理后新execution重试、旧资料解析、普通身份/范围拒绝、Q/L受控私有快照/安全学生投影有证据。SDK实际原始字节、Blob、预检hash、重复封存409通过。历史首次cursor失败保留，没有把所有历史运行都改称成功。
- A复核14个Linux wheel对锁hash、9个image执行源码对Git内容及纯闭包指纹；无SQLModel/应用配置/语音模型，实际seals15/work44MiB。C已交固定79接缝只读复核无阻断，非动态或G独立验收。
- 跨工作树契约工具只允许登记A副/独立树/active包使用候选环境，其他角色保留共享环境与锁检查；A已读最终修复。T1静态迁移/注册/schema检查与已接收463来源保持。

原始交接见候选 `others/docs/c1-public-handoff.md`，OS交接 `labconnect-c1-t2-m2-b7b27c7-handoff.md`；本机A回执 `others/reports/c1-t2-receipt/final.json`。这些是候选接收记录，不代表main运行、三端原生保存或云端更新。

## 当前接棒

现有prepare/profile与Prepare脚本仍面向A副候选venv，需最小严格main模式和实际迁移头输出；主线运行准备不能重写受跟踪许可证/源码。P1工具改动只在A副树提交，A接收后给准确main SHA才进入P2。迁移保留原库/数据/ID/owner分离，激活已经验证的两套共享环境与原18767，实测新旧入口和普通合成闭环，再按最终main重建受影响三端。

正式B2/D2基线须等待实际main、固定版本/学生DTO/受控服务及来源证据；专业60题/六关仍是待审核草稿，合成验证不冒充专业人工审核。B2/C2/D2、新原生、G、ECS与Git推送门禁保持。

## P1启动工具候选（待A合入）

A副按 `21db8c558e46b82ea79aa45bbf08a522d7f9d5d6` 委托补齐工具：prepare/启停/探针按固定profile选择；main仅真实primary/main，固定共享worker、`runtime/content-parser`及18767；C1候选仍独立18768且保留原角色校验。main运行准备只比对已接收锁、14包安装版本和许可证据，许可不一致直接失败，不重写跟踪资料。镜像/协议切换须原journal每条均已实际停止且released，原实例/key继续使用。

迁移入口在升级事务内读取实际alembic头并输出。新增 `Open-C1-API.cmd` / `Start-C1.ps1 -NoOpen`，复用Start-A1的API目标、真实来源与健康检查；主线v2尚未准备则明确拒绝，默认打开8000/docs。网页资料保留原入口；Verify在main/C1仅报告能力/源码/镜像检查，不冒充旧完整sandbox验收。

P1仅工具及只读/合成profile检查，未执行main准备、依赖激活、控制器切换、备份迁移或三端构建。准确候选提交和最小检查见A副最终回执及 `others/reports/c1-public/post-main/p1/`；只有A接收并发送第二个完整main SHA才执行P2。
