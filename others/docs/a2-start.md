# A2 开工基线与分阶段交接

唯一总控A使用main，B/C/D使用已登记外部工作树及codex/b-core-a2、codex/c-content-ai-a2、codex/d-learning-ui-a2。ownership的worktree=null表示按Git registry查分支，本机路径由workflow报告，不写死公共契约。旧task/*树、未指派detached树和历史标签保留。

历史a1-0.1.0/checkpoint-1不变；a2-start= dfd087d的完整值用git rev-parse a2-start核实（准备工具基线，不代表业务完成）。**A0完成后使用新的本地a2-ready**，其完整SHA用git rev-parse a2-ready取得，A在最终报告公布并同步三棵干净角色树。旧标签不覆盖；后续每次公共集成再发布新的完整SHA，B/C/D保留提交后合并。

## 固定顺序

1. **A0公共执行基线**：兼容CourseCatalog/教学班、工作身份/学生互斥、前端会话和页面/预览协议、真实0.2.0 SDK、CORS、共享依赖/ASR与测试归属。实际检查见[a0-handoff.md](a0-handoff.md)。
2. **B1**：组织账号、目录班级、名单/审批/协作/交接/归档、授权服务和教师/管理页面组件；A及时集成迁移/真实接口/SDK，再交C。
3. **C**：授权资料、分层库、审核固定版本/关卡、搜索、学校AI设置和助手。教师账号完成真实问答/中文语音；B2状态未有时学生辅导暂停，避免循环等待。
4. **B2与C联合验证**：正式作答/保存/续答/超时/判分/进度/记录，账号级AI考试暂停与恢复，交D稳定真实接口。
5. **D**：三角色HashRouter工作台、真实页面注册/搜索、六关互动预览与学习考试，独立测试范围web/tests/d-learning/。
6. **A2**：合并联调、更新通用入口及实际Open-A2、重新构建客户端并测九种平台身份组合、真实录音/引用/下载，完成后才checkpoint-2和已授权推送。

四份完整可复制Goal见[任务书入口](ai/README.md)。本轮不自动启动其他聊天；各阶段先合并A最新SHA再开工，公共契约及时交A，D唯一维护公共前端入口。不是B/C/D一起启动再等全部结束才协调。

## 开工条件及边界

~~~powershell
git rev-parse a2-ready
python .\others\scripts\workflow.py status --baseline a2-ready
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
~~~

registered/clean/contains_baseline/ownership_current以及依赖锁一致才就绪。主树配置/依赖共用、源码各树绑定，见[共享环境](shared-environment.md)。角色只能提交本分支本范围，不自行推送，保护已有提交。

A0不是B1或A2完成。当前真实API0.2.0仍没有资料搜索、考试或管理全业务；未来协议只在[a2-protocols](../contracts/a2-protocols.md)和TS声明。完整监控交E、签名/正式安装器交F。Windows/Android麦克风与采集、中文确认问答播报和文件适配在C/D交付后由A/F真实测试，不以worker示例代替。最终包必须对应A2源码及契约，准备阶段不额外推送。
