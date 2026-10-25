# C1 M1领域候选交接

这是已手动首启C1的领域候选，不是整包完成、main接收、B2放行或真实PG/API已通过。原C02后端/worker仍由A副接续，C没有恢复旧包。完整目标见c1-plan.md，各轮范围与检查见c1-progress.md；本轮冻结提交SHA由Git及发给A的消息确定。

## 输入、实际范围和证据

- C树D:/codex/worktree/ffb2/SafeLabPlatform，codex/c-content-ai-a2；已保留原ecb7129历史并按用户指定普通合并3cdb38310e2c4fbd8a514384b6670062752ef1eb，没有推送。
- 本包只写content/questions与content/lessons新模块；没有改旧content顶层/worker、B、D、迁移、公共模型注册、main路由、依赖/SDK或主库。
- 已只读查看A同步的main 29d0d7f92698cb62fc25f1247ecaed21eae8d481及新演示检查范围；没有擅合移动main。shared_env status业务锁匹配、worker锁不匹配，因此未执行/重建共享worker。公共0.4.0接收不代表C1表和路由已激活。
- 运行m1-pure.txt：66项，65通过、真实XLSX往返1项明确skip；Ruff和git diff --check通过。日志/exit在questions/test-results/c1忽略区。14项PG候选未运行；没有SQLite替代、迁移、真实API origin或SDK通过结论。
- 本轮正常文件I/O使用真实临时PrivateStorage/内核guard；DB授权/事务回调在这些纯检查中覆盖为测试对象，不代表真实授权与回滚已通过。现有TestClient/httpx弃用提示保留，不擅改共享依赖。

## 已交领域内容

题库草稿/固定QuestionVersion、四题型、审核与目标发布、授权过滤/分页、复制/引用/退用及不可删除的许可来源链；关卡草稿/固定LessonVersion、独立选择/热点/排序、受控教师预览与被动SVG、题目版本与来源台账；导入批次/任务、CSV/XLSX编解码及固定CLI、预检绑定/原子确认、导出清单/再鉴权、取消/受控重试、本地上传下载流。详细接缝见c1-http-candidate.md、c1-transfer-format.md。

60道原创草稿、两个示范班各三关及六份原创SVG/短课已交，未专业审核/发布。静态数据、来源许可与内部原子导入见c1-demo-drafts.md，不作为学生公开资源。新增模块不替代原资料检索或C02的解析能力。

## A副2：模型/迁移与公共接入

先由A发布具体委托及准确执行SHA；C没有给A副自动越权。A副2接领域候选后可先完成迁移和真实专用PG入口，再交C跑领域PG，不以“C1先全部PG通过”循环等待。

1. 注册questions.models的11张表、lessons.models的12张表，按SQLModel真实FK和索引拓扑迁移；与当前c02d0c00001及后续实际迁移头串接。不要把C旧0.3.2当新的公共头。新增TransferTask.input_sealed和ExportVersion有序唯一约束均在候选模型内。
2. 保留现有学校/学院/课程、MaterialVersion/SourceChunk及账号会话ID。新增表不重建原库、不自动填入主库示范数据；owner迁移与API非owner配置分离，基础兼容回归按现行演示规范执行。
3. 固定QuestionVersion/LessonVersion、SceneAsset及固定来源/题目关系/题目来源台账在事务完成后不能更新、删除或追加改变语义的子行；允许同一创建事务完整填充快照。草稿可编辑但已有来源台账不能在“解除题目引用”时被清除；整份未发布草稿放弃可按服务删除，固定台账继续保留。迁移须用真实PG落实，不以纯payload hash代替数据库保护。
4. 父记录归属、creator和版本对应关系不可重写；审核version/target/submitter/statement绑定不可漂移，submitted只允许一次决定；发布绑定必须是对应approved审核，停用只改自身状态。目标发布V与源主记录V分开，不授予教师跨学院整库管理。
5. 原始材料引用仍指向真实版本/chunk并验证归属与定位；关卡题目引用使用真实question_version_id，固定内容/答案须匹配。注意已审核公共版本的跨校独立复制可以保留原私库来源FK作为许可历史，不能用“一律同校FK”误拦，也不能因此授予原文件R。新跨校选择仍须当前真实公共发布，客户端许可字段不能充当批准证明。
6. ImportBatch/TransferTask的school/library/owner/login/work_role、输入hash、文件key和导出清单在任务生效后不可漂移；重试只按新generation/明确状态清旧结果，不覆盖已committed批次。确认草稿及ImportCreatedQuestion映射一笔事务，命令回执只含最小ID/状态/数量。
7. 在公共入口挂载两个候选router，注入C1Environment及TransferIO。budget须来自本次操作前的真实磁盘探针；不在quota事务中做文件I/O，也不能永久缓存启动时空闲容量。代码中的缺环境/缺配额/缺准入503是实际不可用状态，不能换成空成功回调。更新真实OpenAPI/SDK后才交D消费。

## A副2：队列、runner与计量

- TransferAdmission统一检查C02/C1全局队列、owner上限和跨模块接收槽；C没有另开部署或自管第二队列。streaming.receiving_count给出两类上传的合计，A也须接入C02原接收检查并在同一quota_lock执行，避免只有C单向检查。
- 固定CLI、挂载和结果协议见c1-transfer-format.md。import只消费真实封存原件，export私有输入必须在实际执行前重新鉴权并重算同一manifest hash。输入/输出都由可信控制端有界读取；stdout退出非0是失败，不能把错误JSON当成功预检或可下载文件。
- 可信控制端在新generation中记录真实execution_id/lease_owner；沿用现有重任务排他和固定任务启动模板，不接受用户命令/镜像/路径。发起、轮询、停止、确认清理及恢复均按实际执行ID匹配；不能仅靠租约过期宣布旧进程停止。
- import结束：读固定runner真实有界Preview，确认执行已退出后，在匹配的running代次/租约下调用imports.ingest_preview并提交；之后完成清理和stop_confirmed/预留释放。其服务不自行提交，不释放预留。超时/失败/取消由控制端写明确状态，迟到结果不能覆盖新代次。
- export结束：按原清单再次判权，验证实际文件类型、长度/hash和对应格式上限后，使用同task内核guard和opaque .part→.blob封存；只在匹配执行代次下写succeeded/result_hash/result_bytes。结果不能覆盖既有文件；失败保持无可下载成功结果。
- C1未启动上传的恢复可调用streaming.reap_upload，只有获得真实guard、完成清理并成功写DB后才返回true。出现execution_id的任务仍由可信runner停止/清理，不能用此上传清理函数代替stop receipt。封存原件可在明确取消后保留为计量retained，重试前须stop_confirmed且reserved=0。
- 原件、预检数据库行、草稿/固定版本、场景、任务manifest、导出、临时副本及失败残留计入统一学校/公共/全局额度。Task.reserved_bytes与retained_bytes、ImportBatch.retained_bytes及各内容retained_bytes都纳入，不能漏计。已删除物理文件但DB确认失败时仍保留预留，后续恢复再确认。
- 32MiB是任务工作预留，不可凭纯测试宣称覆盖峰值。openpyxl会使用临时存储，A须定向到受控计量目录并核对实际导入/导出峰值；不足时明确失败，不静默截断、不写未计量副本。锁定openpyxl3.1.5、defusedxml0.7.1及传递依赖/许可，并跑被跳过的真实XLSX往返。保持原无网/非root/只读根等现有保护，但按用户最新决定不追加完整攻击压力矩阵。
- Caddy/请求大小例外只放行确切PUT /api/v1/content/questions/tasks/{task_id}/input的5MiB上限；CSV实际任务仍1MiB，不能放宽整个content。上传完成先验证真实长度/hash，已封存重复PUT返回409提示查询任务，不覆盖原件。实际字节流不长期持有认证依赖的Session。

## B2/D与后续完成条件

B2只通过questions.assessment.resolve_assessment_questions和lessons.assessment.resolve_lesson_publication读取私有固定评分/素材快照。官方学生JSON/SVG均由B2按实际任务、版本、当前关系与解锁授权；C未注册学生通用答案或裸资产接口。student_lesson_from_snapshot只做当前材料引用过滤，不替代B2任务授权。

D消费A正式生成SDK和teacher-preview DTO；C1应用内页面、路由、学生互动及三端渲染仍归D。SVG静态源可供D预览设计，但私有评分清单/含答案CSV不进入web静态目录。A副2提交真实公共技术SHA后，C同步准确基线、在其迁移/非owner PG入口跑14项领域候选及必要正常流程修复；A副2补正常HTTP/SDK和已有功能回归，再由A发布B2/D2真实内容基线。M1到此仍不是C1完成，不自动启动助手/监控或B2。
