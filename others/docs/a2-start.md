# A2 开工基线与分阶段交接

唯一总控A使用main，B/C/D使用已登记外部工作树及codex/b-core-a2、codex/c-content-ai-a2、codex/d-learning-ui-a2。ownership的worktree=null表示按Git registry查分支，本机路径由workflow报告，不写死公共契约。旧task/*树、未指派detached树和历史标签保留。

历史a1-0.1.0/checkpoint-1不变；a2-start= dfd087d的完整值用git rev-parse a2-start核实（准备工具基线，不代表业务完成）。**A0完成后使用新的本地a2-ready**，其完整SHA用git rev-parse a2-ready取得，A在最终报告公布并同步三棵干净角色树。旧标签不覆盖；后续每次公共集成再发布新的完整SHA，B/C/D保留提交后合并。

## 固定顺序

当前[B1最终集成交接](b1-handoff.md)已完成，真实契约0.3.1。用户随后确认先改已有UI：设计候选UI-2026.10-v1等待网页图片批准，登记和批准状态见[UI改版协作](ui-redesign-coordination.md)及[辅助任务登记](../contracts/auxiliary-tasks.json)。旧b1-ready不是立即启动C的许可；C/B2新增功能等待既有UI经A验收。a2-ready及b1-ready均保留原历史位置。

1. **A0公共执行基线**：兼容CourseCatalog/教学班、工作身份/学生互斥、前端会话和页面/预览协议、真实0.2.0 SDK、CORS、共享依赖/ASR与测试归属。实际检查见[a0-handoff.md](a0-handoff.md)。
2. **B1（已完成）**：组织账号、目录班级、名单/审批/协作/交接/归档、授权服务和教师/管理组件；A已集成并发布b1-ready=1e1011b4ff2e3c5a66b22492fb87a671e9699584。
3. **网页图片批准（当前）**：独立设计支线仅在others/design/ui-redesign/出全部已有页面及重要表单/弹窗/状态图。候选生成或渲染通过不代表用户批准，不提前合入main或迁移产品。
4. **规范冻结**：网页获批后补390px移动稿、视觉/组件/状态规范、功能映射及素材许可；A分别记录桌面批准SHA与最终交接SHA，再发布D-UI基线。
5. **D-UI → A验收**：原D牵头已有UI公共壳/设计系统/正式导航，B按所有权迁移教师管理展示层，F配合原生适配；保留真实功能与权限，A重建并实测相关客户端。通过后才发布允许C开工的新完整SHA，不在此阶段实现题库/考试/语音等新业务。
6. **C**：授权资料、分层库、审核固定版本/关卡、搜索、学校AI设置和助手。教师账号完成真实问答/中文语音；B2状态未有时学生辅导暂停，避免循环等待。
7. **B2与C联合验证**：正式作答/保存/续答/超时/判分/进度/记录，账号级AI考试暂停与恢复，交D稳定真实接口。
8. **D后续接入**：完整三角色工作台、真实资料搜索、六关互动预览与学习考试，沿用批准风格及已有壳；独立测试范围web/tests/d-learning/。
9. **A2**：合并联调、更新通用入口及实际Open-A2、重新构建客户端并测九种平台身份组合、真实录音/引用/下载，完成后才checkpoint-2和已授权推送。

完整可复制Goal及D-UI前置目标见[任务书入口](ai/README.md)。本轮仅登记已存在的设计支线，不自动启动D/C/B2；获准阶段先合并A公布的最新完整SHA，公共契约及时交A，D唯一维护公共前端入口。

## 开工条件及边界

~~~powershell
git rev-parse a2-ready
python .\others\scripts\workflow.py status --baseline a2-ready
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
~~~

registered/clean/contains_baseline/ownership_current以及依赖锁一致才就绪。主树配置/依赖共用、源码各树绑定，见[共享环境](shared-environment.md)。角色只能提交本分支本范围，不自行推送，保护已有提交。

A0不是B1或A2完成。A0历史契约为0.2.0；当前B1公共契约0.3.1已接入组织账号/班级后端及教师/管理独立组件，正式导航由D接入。资料搜索、考试等后续协议只在[a2-protocols](../contracts/a2-protocols.md)和TS声明，尚未冒充真实接口。完整监控交E、签名/正式安装器交F。Windows/Android麦克风与采集、中文确认问答播报和文件适配在C/D交付后由A/F真实测试，不以worker示例代替。最终包必须对应A2源码及契约，准备阶段不额外推送。
