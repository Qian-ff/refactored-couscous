# C-02 v1.1 执行进度

完整工作目标以用户手动提交的附件 goal-objective.md（a9f020e7-dacb-4999-ab40-0aa8a6aa390c）为准，不恢复旧整包Goal。

## M0 已核验
- 实际gpt-6.1-sol / Default / medium（当前轮turn_context）。
- C / codex/c-content-ai-a2 / D:/codex/worktree/ffb2/SafeLabPlatform。
- 已从157b99c0bf69af7e0830d8109dcbb3e3398c4251安全快进到f516ef7abc66078325f103785c3c2e760441a56b。
- workflow：C registered/contains_baseline/ownership_current/ready均true。
- shared_env：backend/web/worker inputs match均true；probe确认本树app源码。
- 普通沙箱Git元数据写入和主树路径查询受限，授权进程成功完成同步及核验；没有修改系统安全设置。

## M1 进行中，尚未交付
已新增worker content/protocol.py：内部labconnect.parse/1结果编码，8192字符分片保留原位置，正文/块/输出预算及哈希。没有注册公共接口或SDK。

检查：共享3.13环境执行content.test_protocol，5项通过；共享Ruff检查worker content目录通过；git diff --check通过。仅证明协议合成测试，不是四格式解析、PG或受限上传验收。

第二轮增加四格式CLI候选、严格TXT编码解析、OOXML实际读取预算/路径/宏/DTD预检及content.verify。14项可信合成测试通过；verify因缺解析依赖退出1，报告明确四格式正常集成和sandbox尚未通过。CLI不是受限运行适配器。依赖/许可及边界见worker content/README.md。

第三轮新增8个领域模型、基于B的版本可读SQL与详情二次判权、真实父级推导及ParseRunner候选能力协议。4项元数据/SQL编译和2项能力检查通过；不涉及PG或容器运行。约束待接入项见c-02-model-notes.md，尚未提交公共接入候选。

第四轮新增严格输入DTO、配额汇总/预留检查及短命令服务：库创建/改名启停、知识点新版本/任务、提审/审核/发布/绑定停用。复用B命令事务、幂等回执和审计，事务内清除预读缓存后重新判权；审核人仅凭真实目标V通过对应提审绑定读取固定待审核版本，不给予S或学生草稿权。

纯检查累计15项通过（4模型SQL、2runner、9输入/配额/许可），Ruff和差异检查通过。另新增3项真实PG服务场景候选，尚未运行：S不能建学校库、固定发布/v2草稿隔离及停用、幂等冲突。不得把未运行的PG测试当成通过。

第五轮新增PrivateStorage、上传输入/状态/取消、两步接收/封存候选及后台身份重载。传输不保留DB会话，5秒续租、20秒租约、30秒空闲及5分钟期限；同upload写入排他、全局两个接收槽位、真实哈希/长度检查和重复正文校验；预留只在确认关闭写入和删除无引用文件后释放。取消等待线程I/O实际结束，磁盘/清理失败保持安全错误与占额。

新增6项上传/文件系统/线程取消纯测试通过，包括真实5秒慢输入续租；原15项中的模型4项和输入9项回归通过，Ruff和差异检查通过。未进行PG上传/并发或故障接管验证。失联writer不凭过期租约释放，仍须补权威停止确认及恢复路径；不能把未验收上传候选视为可发布。

第六轮新增严格解析结果校验、任务取消/重试/成功版本重解析、持久化claim/heartbeat/快照/故障/恢复事务和lifespan调度候选。execution_id启动前持久化，旧generation不能覆盖快照；runner未确认停止不启动替代重任务，未确认release不释放临时预留。服务端校验输出格式、来源定位/分片顺序、哈希和体积，不信任worker任意字段。

新增7项结果边界和3项调度停止/清理确认纯测试通过。PG调度/租约竞争与实际runner均尚未运行；A需实现固定execution_id幂等/停止终止凭据及release确认，见模型交接草稿。领域代码仍未挂载。

第七轮增加类型化候选路由、运行注入接口、读取/管理投影和鉴权下载。阅读库按真实R/V及实际版本/发布绑定筛选；submit-targets提供S最小元数据并二次对象校验；最新版本在授权后选择，避免v2草稿遮蔽可读v1。页段按1MiB响应预算继续分页。原件先校验字节/哈希，传输每块重验当前登录/身份和版本授权，不保留DB连接；不返回内部存储key。

35项业务纯测试通过（包含新增4项查询SQL/候选OpenAPI/投影边界检查），没有发布正式OpenAPI/SDK。另新增3项真实PG查询场景，尚未运行。worker新增四格式真实CLI合成夹具，当前15项通过、3项因缺依赖跳过，verify明确退出1，parser.json仍标明未通过四格式/沙箱验收。测试日志及实际退出码保存others/reports/c-02/。Ruff及差异检查通过。

A已完成关键裁决：上传使用同卷稳定文件锁，Linux flock/Windows LockFileEx；清理取得同一guard后失效旧generation并删除/结算，不用额外宿主停止探针。ParseRunner固定execution_id、持久终止凭据及release清理任务副本获同意。完整执行补充见c-02-accepted-addendum.md，尚未实现文件锁与进程竞争测试，不视为M1接收。

第八轮完成稳定UploadFence和孤立上传恢复候选：Windows LockFileEx/Linux flock，所有写入/封存/清理持同guard；真实线程取消、独立进程竞争、冻结进程持锁、终止恢复5项新增检查通过，业务纯检查累计40项。错误保留预留，scheduler记录安全清理错误。尚未进行PG迟到写入/文件-DB中断竞争，不能以锁原语测试代替完整恢复验收。

模型新增班级完整父级和真实会话owner复合FK，所需核心UNIQUE交A；目录条件父级、不可变历史、成功快照、审核发布和延迟封存约束候选见c-02-guards.sql。save_snapshot先flush chunks再冻结成功版本。新增3项PG guard测试候选未运行。完整M1候选交接见c-02-integration.md；M1前不实现依赖尚未生成SDK的前端。用户最新要求：完成C-02后停止，不启动后续模块。

未完成：格式解析、沙箱运行、领域业务、真实PG/HTTP、迁移/公共接入/SDK、前端和M2/M3全部待续。不得标记整包完成。未安装依赖或执行迁移/云模型。
