# C1候选接收与主线激活准备

2026-10-26后续更新：[cd1/0.5.0云端部署亦已验收](c1-cloud-handoff.md)，GitHub部署源码已推送；本页仍分别保留本机bae实测及当时尚未执行云部署的历史记录，不把云端cd1冒充原生bae产物。B2/D2/C2依[消费者基线](c1-consumer-baseline.md)手动首次启动。

2026-10-26，A已核对T2候选 `b7b27c72c1fdfccd434663f2fc683b5576202967` 和P1工具候选 `58b5d26ece3cd8e076eaaf8d9034b7ca511988d2`，统一接收至main。**当前C1主线基础接入已验收，实测功能/产物来源为 `bae3461a0e4cba9f6de8b13d12899a965a66b77b`，契约0.5.0、迁移c1d0c000001。** 原库保留、两套既有共享环境激活、普通主线流程和三端基本访问通过，具体范围见下文P2；[消费者基线](c1-consumer-baseline.md)发布技术依赖，新模块仍需首次手动启动。

## 接收依据

- 实际候选API8002来源b7、0.5.0/c1d0c000001，与私有18768及image、网页产物分别有准确记录。A实际GET identity/health及OpenAPI；规范化OpenAPI与提交字节一致，SHA256 `656462a90a893433a4841a9516f5145d19c1dfed0f8581969affbb1ca839d5f4`。
- 不可变清单 `others/reports/c1-public/t2/manifest.json` 在A副树，hash `70c8a9e073bac30511da2c2e479e3ecceb29a076153e0c27c2fb423260d9dc76`；A核对17附件、7个来源文件hash全部匹配。原M1六附件及此前T1/C领域证据保留。
- 结果按源码区分：79c6后端14项＋15子检查；0cf实际公共HTTP/runner/PG两项；最终b7工具选择QA、契约/类型/构建及生成SDK浏览器一项。0cf→b7的backend/app与web/src实际无差异；没有把旧M1改称新全矩阵重跑。
- 实际CSV/XLSX导入预检—确认草稿—审核发布—固定导出往返、运行中取消/停止清理后新execution重试、旧资料解析、普通身份/范围拒绝、Q/L受控私有快照/安全学生投影有证据。SDK实际原始字节、Blob、预检hash、重复封存409通过。历史首次cursor失败保留，没有把所有历史运行都改称成功。
- A复核14个Linux wheel对锁hash、9个image执行源码对Git内容及纯闭包指纹；无SQLModel/应用配置/语音模型，实际seals15/work44MiB。C已交固定79接缝只读复核无阻断，非动态或G独立验收。
- 跨工作树契约工具只允许登记A副/独立树/active包使用候选环境，其他角色保留共享环境与锁检查；A已读最终修复。T1静态迁移/注册/schema检查与已接收463来源保持。

原始交接见候选 `others/docs/c1-public-handoff.md`，OS交接 `labconnect-c1-t2-m2-b7b27c7-handoff.md`；本机A回执 `others/reports/c1-t2-receipt/final.json`。这些是候选接收记录，不代表main运行、三端原生保存或云端更新。

## 接入要求与后续接棒

P1已补严格main模式、只读许可核验和实际迁移头输出，A已接收；主线运行准备不能重写受跟踪许可证/源码。P2须消费A实际发送的准确main SHA，迁移保留原库/数据/ID/owner分离，按已接收锁激活两套既有共享环境与原18767，实测新旧入口和普通合成闭环，再按最终main重建受影响三端。先核对真实进程与Docker/PG状态，服务未运行时恢复原实例和卷，不用候选库替代。

上述P2要求现已完成，实际main、固定版本/学生DTO/受控服务及来源证据见下文与[消费者交接](c1-consumer-baseline.md)。B2/D2技术依赖门禁已满足；B2/C2/D2仍须用户手动首次启动。专业60题/六关仍是待审核草稿，合成验证不冒充专业人工审核；新原生、G、ECS与Git推送门禁保持。

## P1启动工具接收

A副按 `21db8c558e46b82ea79aa45bbf08a522d7f9d5d6` 委托补齐工具：prepare/启停/探针按固定profile选择；main仅真实primary/main，固定共享worker、`runtime/content-parser`及18767；C1候选仍独立18768且保留原角色校验。main运行准备只比对已接收锁、14包安装版本和许可证据，许可不一致直接失败，不重写跟踪资料。镜像/协议切换须原journal每条均已实际停止且released，原实例/key继续使用。

迁移入口在升级事务内读取实际alembic头并输出。新增 `Open-C1-API.cmd` / `Start-C1.ps1 -NoOpen`，复用Start-A1的API目标、真实来源与健康检查；主线v2尚未准备则明确拒绝，默认打开8000/docs。网页资料保留原入口；Verify在main/C1仅报告能力/源码/镜像检查，不冒充旧完整sandbox验收。

P1候选 `58b5d26ece3cd8e076eaaf8d9034b7ca511988d2` 的13个修改路径均在委托内；A核对5份检查日志和13个源码Git blob哈希全部匹配，清单SHA256 `ded9a3321666a878e55871eb3a30c76f9a973e740d102d073d85ffcfa307d0fe`，并独立复跑4项profile QA通过。6脚本解析、Ruff/diff及候选worker的14包只读许可/版本核对已有记录，未把候选环境核对记作main依赖激活。

P1未执行main准备、依赖激活、控制器切换、备份迁移或三端构建。证据在A副树 `others/reports/c1-public/post-main/p1/`；只有A实际发送第二个完整main SHA才执行P2。P2源码若需修复，仍由A副分支提交交A接收，最终构建对应接收后的准确源码，不直接改main。

## P2主线基础接入接收

A先发 `852d57a6ae780b6433279354110ce165bf08b82b`；实际控制端首启发现服务端仍把v2限定18768。A副在允许的control.py及QA内提交 `fe319823b0d792dbaf562e8e8e1c4198ccf110ce`，A复核并独立5项QA通过，接收为最终功能源码 `bae3461a0e4cba9f6de8b13d12899a965a66b77b`。失败日志和旧阶段来源保留；没有把首启失败称通过。

- 恢复原PG容器/原卷，原库custom备份788087字节，SHA256 `09429240db61587377630f86d1e971599bb7d3c8cee0670e41ce71a4af5667c4`。pg_restore --list通过；未执行实际还原。初始23表/10042行，兼容迁移后、合成验证前22旧业务表含ID的计数/内容摘要一致，新旧总46表。A独立核对原备份文件hash、实际主库迁移头及运行角色无owner权限；owner不进应用配置。
- 两套既有共享venv按接收锁离线激活，旧包版本保持。原控制key/instance/root及60条历史保留，切18767/v2后最终63条执行全部停止/released、reserved0。ASR/模型未改，候选端口分离。
- 实际bae主线通过新旧-NoOpen入口、CSV导入预检/确认草稿/审核发布/固定导出回读、研发合成Q/L固定发布/受控快照/学生安全投影、学生私有访问403及旧资料解析/读取。A实际GET核对API/Web源码身份和健康，OpenAPI规范化hash为 `656462a90a893433a4841a9516f5145d19c1dfed0f8581969affbb1ca839d5f4`，并实查控制源码/镜像能力；能力探针不称完整sandbox验证。
- 最终Web production166文件、Windows测试包和Android debug均来源bae/0.5.0；三端真实学生登录、检索、资料正文加载通过。Windows为隐藏DOM，安卓仅项目模拟器；初次只等待弹窗的记录单列保留，最终检查明确等待实际正文。原生流水线的debug网页资源与最终production分别记录，结束恢复production产物，不混用哈希。
- A核对最终静态清单41附件和7源码Git blob全部匹配，另核对备份、166网页文件、Windows exe/app.asar及APK实际文件hash和APK内build-info；已查看网页/安卓原生截图的正文。清单在A副树 `others/reports/c1-public/post-main/p2/manifest.json`，SHA256 `462362f5d1d26d6dd8eb930ab14b681ec9b75e1c1c71ef13d002b7bceaa01927`；A本机回执 `others/reports/c1-main-receipt/receipt.json`。未把live日志哈希当静态证据。

实际产物源码始终为bae；本次接收/调度文档提交仅刷新确认归属的main API/Web启动身份，源码指纹相同，不重建或改写旧报告。Windows可见窗口、原生持久保存、物理安卓、题库/考试/助手UI、完整语音、G、监控、ECS及Git推送均未由本次完成。消费者使用[固定样例及真实服务](c1-consumer-baseline.md)，新模块首次启动规则保留。
