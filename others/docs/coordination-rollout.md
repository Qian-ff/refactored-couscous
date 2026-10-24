# 协作规范 v1 接收记录

2026-10-23，用户在“多线程ai使用梳理”明确批准并要求实际实施。实施起点main为8ad3304efee683e2a8d493673954085bd7b8cdcb；主树干净，A主线空闲，其余角色未运行。本文只记录已完成证据，尚未完成项目明确保留。

## 实施状态

规范/工具：已落地五个业务角色及A-executor委托、E/F历史停用与C监控范围；A副checkpoint必须匹配main批准的具体工作包。统一规范、模板、当前入口与原生职责已同步，冻结设计文件无改动。

实际检查：workflow专项22项通过；协作/共享环境全套unittest共29项通过（含共享数据库锁、树绑定、错误身份/范围、过期授权、停用角色及暂存/空提交保护）。准备/本地链接与11条忽略检查通过；Start-A1 PowerShell语法通过，真实配置导入确认原5173及新增5177 CORS仍存在。受限进程保留既有Python卷路径stderr警告，检查退出成功；未修改系统运行时。

Ruff初次发现准备脚本已有unused sys导入，删除后复查通过；先前人工检查命令中的模块调用和PowerShell嵌套引号错误已纠正，未当作通过证据。规范/工具正式提交为f586b9c6d09623c9e26045104244fed800c4fd46；本记录和委托收尾另见Git后续提交。

A副实际迁移完成。第一次应用提示存在pending composer state；用户确认没有可见草稿后重新调用同一迁移，成功，未发送或删除用户草稿。操作ID exec-7d5213c1-e4bf-4340-afbc-22e265bece55，终态success/revision16。

应用迁移将原聊天01a15e27-4a94-79f0-9a2b-37b3fcee6334替换为目的聊天01a16921-9ff8-7781-bdb8-6ede3d015d6c，名称仍“A子聊天”，项目归属保持SafeLabPlatform；后续只向目的ID发A副任务。原ID仍在历史批准记录中保留，不改写旧设计证据。

实际新树D:/codex/worktree/0aed/SafeLabPlatform，应用生成codex/a分支后，在确认干净、HEAD等于正式规范提交且目标分支未占用后创建codex/a-executor；codex/a保留。workflow登记确认同仓库、clean、contains_baseline、ownership_current，契约0.3.2/所有权5。旧B/C/D和E/F/G历史树未重置或删除。

shared_env status确认backend/web/worker锁输入一致、共享配置及合成账号存在；probe显示共享业务解释器但app_source为新树；probe-worker显示独立共享worker解释器、sherpa/core1.13.8及本树worker源码、主树模型缓存。web-environment实际导入确认5177，独立API使用8002。

临时在新树启动真实API，GET /api/v1/dev/identity确认完整SHA/契约/指纹及worktree_id匹配A副，区别于主树；Origin http://127.0.0.1:5177的OPTIONS预检实际200并返回正确allow-origin。未迁移数据库、未调用业务或云AI。临时进程45780和8002监听已核实退出。共享数据库锁的竞争拒绝/释放及源码隔离由本轮29项测试覆盖。

为补齐独立网页环境，随后在新树使用Use-ProjectEnvironment及shared_env install-web，按锁文件从主树缓存离线硬链接418包，downloaded=0，未运行安装脚本或变更锁文件。实际启动Vite默认5177，HTML HTTP200，网页identity完整匹配A副SHA/树ID/指纹，区别于主树；旧Start-A1在A副树实际触发专用保护，未误用8000或执行演示库迁移。网页与API临时进程均已关闭。证据web-smoke.json与api-smoke.json留忽略区；本次不冒称前端生产构建、UI业务验收或完整原生三端通过。

## 五个聊天的实际同步

以下host均为local，五份规则消息均带明确model/thinking参数发送并收到最终回执；本轮未启动G。均仅只读确认，没有恢复旧业务或派活。

| 聊天/身份 | 当前thread ID | 回执时目录/分支 | 实际model/effort/mode |
|---|---|---|---|
| A主线 / A主 | 01a1544b-7eb1-77f1-9f83-52fa8510503c | D:/SafeLabPlatform / main | gpt-6.1-sol / max / default |
| A子聊天 / A副 | 01a16921-9ff8-7781-bdb8-6ede3d015d6c | D:/codex/worktree/0aed/SafeLabPlatform / codex/a-executor | gpt-6.1-sol / medium / default |
| B副1 / B | 01a15942-8360-7ef1-bf9a-4546a6d6cc1a | D:/codex/worktree/50c8/SafeLabPlatform / codex/b-core-a2 | gpt-6.1-sol / medium / default |
| C副2 / C | 01a15942-9518-7660-a13c-6b5711d08ef6 | D:/codex/worktree/ffb2/SafeLabPlatform / codex/c-content-ai-a2 | gpt-6.1-sol / medium / default |
| D副3 / D | 01a15942-a1c7-7d33-951d-4dbe62d858f7 | D:/codex/worktree/f024/SafeLabPlatform / codex/d-learning-ui-a2 | gpt-6.1-sol / medium / default |

实际设置不是仅依赖回执：逐个读取相应会话JSONL的最新turn_context，确认gpt-6.1-sol、max/medium及default。证据在忽略区others/reports/coordination-v1/runtime-settings.json，包含来源文件、行号、轮次和时间；完整五份回执在receipts.json；真实API和网页证据在api-smoke.json、web-smoke.json。不修改会话文件、全局配置或默认值。

B/C/D明确报告本树尚未合并新规范基线，分别仍为6682ec37a2543e9e50a1bf400a8d70057351c807、1adfe1c70162547a204c9aeb7c7ce4ede8bde1b4、58ab4958e62ca50671be921aa4ce91c9e0c0c1e5，工作树干净；已直接读取主树权威规则。本次仅规则接收，不替其合并；后续执行前由A主安排保存并同步正式完整SHA，工具会拒绝过期规则提交。

Plan/max属于未来规划阶段，本次同步实际均为Default，未把未来档位或模式宣称已切换。新阶段缺少自动Plan切换能力时仍需用户手动操作。

验证委托coordination-v1-validation已完成并关闭；A副未来写入须由A主发布新的active包及明确文件范围，不因迁移获得全仓库权限。下一步仅等待A主/用户制定下一工作包，不自动恢复旧Goal。

当前门禁：C内容与助手允许开工，B2需C交付经A接收；监控、D助手宿主和原生新增不因职责合并放行。无新增push授权。

## 2026-10-24：v2自查分流落地

起点main为f516ef7abc66078325f103785c3c2e760441a56b，工作区和暂存区干净。用户在规范编制聊天逐项确认新流程并启动Goal；A主在只读审查轮次01a16c7a-2145-74e1-866e-60fbd8fe1fbd明确回复“可实施”，无必要补充决定，并确认本聊天落地期间不并行修改相关文件。

本次仅更新[权威规范](coordination.md)、[工作包模板](ai/work-package-template.md)及根入口、角色任务书、阶段/Git导航的冲突表述；模型/全局默认、业务代码、workflow工具、所有权、具体委托和业务门禁未改。C-01和C-02 v1.1现有约定保留，另按用户指令明确C完成C-02后停止，C-03不自动启动；未来获明确启动指令后才采用新制。

准备检查通过，覆盖当前文档的本地链接、角色/委托范围与11条忽略规则；差异检查通过。纯文档调整未进行业务重建或业务测试。落地提交由本聊天最终回报，Git记录为准；只向A发送一次落地摘要和提交，各角色下次开工或换聊读取，不为本次规则唤醒其他窗口。
