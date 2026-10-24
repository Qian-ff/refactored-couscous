# A2 开工基线与分阶段交接

当前分工与设置见[统一协作规范](coordination.md)：A主/A副/B/C/D/G，E并C、F并A副；此调整不改变下述业务门禁和历史基线。

协作v2只调整后续推进方式：C-01既有成果及接收记录、C-02 v1.1现行Goal/里程碑/A公共接入/独立集成实测/接收要求保留，不重做或重新拆包。按用户指令，C完成C-02后停止，不自动启动C-03；C-03获后续明确启动指令后及其他角色后续任务按统一规范自查分流、合并里程碑。下述带日期的接收状态保留为当时记录，不代替当前任务的实际进度。

唯一总控A使用main，B/C/D使用已登记外部工作树及codex/b-core-a2、codex/c-content-ai-a2、codex/d-learning-ui-a2。ownership的worktree=null表示按Git registry查分支，本机路径由workflow报告，不写死公共契约。旧task/*树、未指派detached树和历史标签保留。

历史a1-0.1.0/checkpoint-1不变；a2-start= dfd087d的完整值用git rev-parse a2-start核实（准备工具基线，不代表业务完成）。**A0完成后使用新的本地a2-ready**，其完整SHA用git rev-parse a2-ready取得，A在最终报告公布并同步三棵干净角色树。旧标签不覆盖；后续每次公共集成再发布新的完整SHA，B/C/D保留提交后合并。

## 固定顺序

2026-10-24 M1接收登记：C提交冻结候选`ecb7129497d1f6a69daf09df6db3f2f30537d7ba`，49文件仅在content后端/worker范围；A已核对提交范围和交接，尚未将代码合入main或宣布业务通过。[公共接入工作包](ai/c02-public-integration.md)已准备，对应委托为planned，本轮不自动委托/唤醒A副。真实PG/HTTP、四格式依赖与沙箱验证仍是接入完成条件；当前契约仍0.3.2，迁移仍b1c0e0a00001。A后续明确启用并在独立集成树实测，通过后才发布供C进入M2的完整技术SHA。C完成C-02后停止，B2等门禁不变。

2026-10-24更新：A已接收[C-01 v1.1内容提案](../backend/app/domains/content/handoff/c-01-proposal.md)，C最终候选`157b99c0bf69af7e0830d8109dcbb3e3398c4251`，本地合并`f9d394856f29adc7cb12c86848df9da033b2f83c`。已明确整库管理须范围V、提交权S只允许有权内容提交，以及教职已发布版本R与草稿读改权限的区别；原T01–T14保留，新增未来T15/T16。此次仅接收模型、权限和候选接口设计，未实现内容业务，也未执行这些未来验收场景。真实契约仍为0.3.2，迁移仍为b1c0e0a00001；一键入口及客户端无需因纯文档接收重建。下一责任身份为C，C-02资料与解析须另行审定工作包并由用户手动首次启动；B2、D助手宿主、原生扩展和监控门禁保持原状态。

2026-10-23当前更新：既有UI与[云端API/ASR接入前置](cloud-asr-handoff.md)已通过A验收，**C允许开工，B2仍等待C交付经A接收**。最新C开工标签c-start-ready，完整SHA用`git rev-parse 'c-start-ready^{}'`核验；C保留本树工作后合并，不覆盖已有提交。云端实际源码717e1d0e5f88071c52b361cf3fa1c3bb09d13697，契约0.3.2，迁移b1c0e0a00001；其后交接/工具提交另计。原D Goal已交付，不重复执行。

A已接收D第二批58ab4958e62ca50671be921aa4ce91c9e0c0c1e5，合并1bcab0d071de53010c06e7f593fde3f0f6781bcd；[existing-ui-accepted](existing-ui-acceptance.md)、student-relations-ready与b-ui-integrated等标签保留原历史位置。

B展示迁移6682ec37a2543e9e50a1bf400a8d70057351c807和D公共组件/学生既有入口现已集成；旧b-ui-integrated、d-ui-components-ready及其他标签保持历史位置。本人关系接口与pnpm恢复历史见[0.3.2依赖交接](student-relations-handoff.md)，本轮正式入口为Open-DUI.cmd。

B1最终集成时的真实契约为0.3.1，当前为0.3.2；UI-2026.10-v1批准与冻结d17b342c53fc054bd298bee356143d3b3ab77af6保持原始字节。当前放行见[辅助任务](../contracts/auxiliary-tasks.json)的product_migration：existing_ui_accepted_by_A=true、C_new_features_allowed=true、B2_new_features_allowed=false。原聚合C_B2门禁已拆为逐角色字段，历史交接中的false不覆盖当前C放行。

1. **A0公共执行基线**：兼容CourseCatalog/教学班、工作身份/学生互斥、前端会话和页面/预览协议、真实0.2.0 SDK、CORS、共享依赖/ASR与测试归属。实际检查见[a0-handoff.md](a0-handoff.md)。
2. **B1（已完成）**：组织账号、目录班级、名单/审批/协作/交接/归档、授权服务和教师/管理组件；A已集成并发布b1-ready=1e1011b4ff2e3c5a66b22492fb87a671e9699584。
3. **网页图片批准（已完成）**：用户明确回复“批准 v1，继续移动稿与规范”，绑定桌面b67ad77cd49c2b5f99d2037e5828c29433ea66a6；[批准证据](../design/ui-redesign/approval.json)已由A核对。
4. **规范冻结（已接收）**：390px移动稿、视觉/组件/状态规范、功能映射及许可已补齐；最终冻结d17b342c53fc054bd298bee356143d3b3ab77af6，清单141文件，完整设计142文件，A发布ui-redesign-ready基线。
5. **D-UI → A验收（已通过）**：公共组件、B展示迁移及D学生加退班/历史均已接收，A独立回归并重建实测客户端，补齐安卓系统返回/软键盘回归。见[实际验收](existing-ui-acceptance.md)。A已另行完成云端API/ASR环境并发布c-start-ready；不把环境就绪冒称题库/考试/助手业务完成。
6. **C**：授权资料、分层库、审核固定版本/关卡、搜索、学校AI设置和助手。按[悬浮助手交接](assistant-floating-handoff.md)提供内容/个人历史/固定范围/语音及宿主回调，取消独立聊天页计划；D仍唯一宿主。教师账号完成真实问答/中文语音；B2状态未有时学生辅导暂停，避免循环等待。
7. **B2与C联合验证**：正式作答/保存/续答/超时/判分/进度/记录，账号级AI考试暂停与恢复，交D稳定真实接口。
8. **D后续接入**：完整三角色工作台、真实资料搜索、六关互动预览与学习考试，沿用批准风格及已有壳；独立测试范围web/tests/d-learning/。
9. **A2**：合并联调、更新通用入口及实际Open-A2、重新构建客户端并测九种平台身份组合、真实录音/引用/下载，完成后才checkpoint-2和已授权推送。

完整可复制D-UI/B-UI及后续目标见[任务书入口](ai/README.md)。另已接收UI-ASSISTANT-2026.10-v1.1冻结78cdeb677ed1f302f1a3ecb68bfbd834aa4b85d1，规范基线ui-assistant-design-ready；它不改变第5步既有UI验收和C/B2门禁。获准角色先保存改动再合并A最新完整SHA，不替角色树覆盖改动；全新模块首次Goal手动启动，已授权模块后续包可自主续办，另行分派遵循统一规范。规划及执行强度按任务性质和AGENTS角色档位核验，不因换包重复max规划。

## 开工条件及边界

~~~powershell
git rev-parse a2-ready
python .\others\scripts\workflow.py status --baseline a2-ready
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
~~~

registered/clean/contains_baseline/ownership_current以及依赖锁一致才就绪。主树配置/依赖共用、源码各树绑定，见[共享环境](shared-environment.md)。角色只能提交本分支本范围，不自行推送，保护已有提交。

A0不是B1或A2完成。A0历史契约为0.2.0；当前公共契约0.3.2已接入组织账号/班级后端、学生本人关系元数据及教师/管理独立组件，正式导航由D接入。资料搜索、考试等后续协议只在[a2-protocols](../contracts/a2-protocols.md)和TS声明，尚未冒充真实接口。完整监控归C后续独立阶段、签名/正式安装器由A副受托承担。Windows/Android麦克风与采集、中文确认问答播报和文件适配在C/D交付后由A主委托A副真实测试，不以worker示例代替。最终包必须对应A2源码及契约，准备阶段不额外推送。
