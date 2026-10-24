# C-02 v1.1 M1：资料与解析候选交接

状态：M1候选，等待A公共接入。不是C-02完成、main接收或B2放行。

## 来源和冻结范围

- C，`codex/c-content-ai-a2`，`D:/codex/worktree/ffb2/SafeLabPlatform`。
- 业务基线 `f516ef7abc66078325f103785c3c2e760441a56b`；真实contract 0.3.2；迁移头 `b1c0e0a00001`。
- 本文件所在提交为M1冻结候选，完整SHA在给A的里程碑消息中提供；不把未提交文件作为交付物。
- 只读核对main `768bc0c5e4587616bdeace369723d23a94ba5dcb`：仅协作文档变化。按v2兼容条款继续现行C-02 v1.1，不合并移动main。
- 仅新增/修改content后端、content worker及其领域测试/交接；没有公共注册、迁移、SDK、正式路由或前端实现。
- 用户最后限定：完成C-02后停止。不得顺带启动C-03、题库、助手、语音、监控或B2。

## A需要完成的公共接入

按已审定Goal，先在登记的独立集成树审查和接入，不能把未验M1直接合入main。A自行发布明确公共工作包；本交接不自动委托A副。

1. 注册`app.domains.content.models`，将8表及下面约束接入兼容迁移。A维护`app/models.py`、核心元数据及Alembic；C未运行任何迁移。
2. A在核心模型和迁移加入命名UNIQUE：`login_session(id,user_id)` / `uq_login_session_owner`，`course(id,school_id,college_id,catalog_id)` / `uq_course_content_parent`。C模型已声明对应会话所有者、班级完整父级FK；旧同校FK保留。不要求班级学院等于目录学院。
3. 审查并迁移本目录`c-02-guards.sql`：不可变历史、条件目录父级、实际源/任务绑定、审核发布及延迟文件封存约束。文件是候选SQL，不是安装器，尚未在PG运行。A决定迁移函数/trigger命名和downgrade顺序；运行角色不能关闭保护。
4. 上传与版本有循环FK：先建表后命名补FK，均NO ACTION/RESTRICT，不用级联删除历史。文件绑定constraint trigger必须DEFERRABLE INITIALLY DEFERRED，因为封存事务先flush版本再更新upload回指；重解析可复用同一原件，不要求每个新版本等于首次sealed_version_id。
5. 固定解析依赖/传递锁/发行包哈希和许可；见`others/ai_worker/content/README.md`。候选版本pypdf6.21.2、python-docx1.2.0、python-pptx1.0.2、lxml6.1.3。A负责项目内安装；C不改锁或系统解释器。
6. A维护配置：服务端私有原件根、任务临时区、受限执行镜像、受信控制适配器连接及启动钩子。不得把真实密钥输出到报告或传给解析进程。
7. A实现`parse_runner.ParseRunner`，注入`app.state.content_runtime=ContentRuntime(factory,storage,runner)`。factory每次返回当前源码对应的新Session；`PrivateStorage`只接受A配置的私有根。缺配置/能力明确不可用，不用普通子进程降级。
8. A lifespan挂接`ContentScheduler(...).serve(stop_event)`并等待关闭：取消、stop、release和清理确认都完成后才退出。跨实例同卷锁、数据库短锁和受信runner排他共同生效。
9. 总入口以`/api/v1`挂载`content.routes.router`；URI候选见下节。A统一operationId/契约，生成真实SDK，初始分配contract 0.4.0，有冲突由A重新公布。不要发布占位SDK。
10. 代理只对准确的`PUT /api/v1/content/uploads/{upload_id}/bytes`放行22020096字节；业务仍20971520。其他JSON/请求限制不扩大。CORS允许实际C 5175来源、Idempotency-Key、工作身份头；暴露Content-Disposition/Content-Length。
11. A在独立树跑真实专用PG/HTTP、四格式CLI、受限执行、权限/取消/恢复、旧功能及前端构建回归。公共测试保持串行库锁；不能用演示库或SQLite冒充PG。
12. A接收后公布完整main技术接入SHA、真实contract/migration、依赖锁指纹、运行配置入口、源码绑定和实际API来源。C再安全同步进入M2；B2门禁保持关闭。

## 领域模型与固定规则

`models.py`：Library、Material、ContentUpload、MaterialVersion、SourceChunk、MaterialReview、MaterialPublication、ContentJob，对应8个`content_*`表。

- 五范围：platform_public、school、college、catalog、course。scope/audience及父级创建后固定；扩大共享用精确版本的审核/发布绑定。
- B的CurrentIdentity/resource_access/read_resource_predicate是唯一授权来源；组织、creator、published从持久资源推导。S仅提交，V管理库和审核目标；教师不能凭S管理整库或他人草稿。
- SQL先授权再搜索/最新版本/去重/计数/分页；v2草稿不遮住学生可读v1。发布与审核目标通过EXISTS，返回授权目标投影，不附源私库组织。
- 空库按V可管理；`submit-targets`按真实S只提供最小id/title/scope，不提供草稿/统计。目标V通过确切submitted/approved审核绑定读取固定待审版本。
- 成功快照不可覆盖、页段不可改删；成功重解析新建version。ContentRef始终引用固定MaterialVersion.id。版本原件与文字输入XOR，不能用file_key代替FK。
- 提审要求成功版本、原件教学授权声明；审核批准核对warnings_hash及整份原件开放授权。公开目标还需明确public_reuse_allowed/license/license_url。学校私库不直接跨校。决定后的审核不可改写；重新提审新增记录。
- 发布绑定精确review/version/target复合FK且review唯一；仅批准并授权原件才能发布。停用须目标V+revision；源Material停用不批量撤销其他目标绑定。
- 成功版本不因旧会话退出而改写；后续读取仍以当前身份/课程关系授权。普通资料不依赖未来B2 AI gate。

## 存储、配额和上传恢复

`storage.py`使用服务端UUID .part/.blob，拒绝路径、符号链接/重解析越根；专用私有根不公开映射。封存为同卷hardlink+unlink且不可覆盖；fsync原件，Linux同步目录。A核验实际卷支持、权限及文件/DB成套备份恢复。

上传JSON创建短事务先授权/预留；PUT流式计数与SHA256，传输不保留数据库连接/事务。上限：PDF/PPTX/DOCX20MiB、TXT/知识点1MiB；同账号1个活跃upload，全局2个接收槽，5秒心跳、20秒租约、30秒空闲、5分钟墙钟、会话15分钟。相同封存upload重复PUT重新流式核对正文后返回原ID，不落盘或重建任务。丢失响应先GET upload状态；失败新建会话，不做分片续传。

配额：学校1GiB、公共1GiB、服务全局5GiB；磁盘保底1GiB扣除未落盘预留；每解析任务预留32MiB。短事务先tenant锁再全局quota锁；未清理残留无论终态仍计量。永久原件/输入/快照单独计量，runner release不扣永久数据。

`UploadFence.try_acquire`为同卷稳定锁文件的Windows LockFileEx/Linux flock。busy保留槽位/预留；unavailable显式安全错误。写入、封存、删除用同guard，取消等待真实线程I/O和句柄关闭。清理先在事务外取得guard，再短事务增加generation并确认无版本引用，持锁删除、短事务结算。锁文件业务永不删重建。迟到_claim取得guard后重新检查状态/身份/代次才写文件。

`reap_uploads`在scheduler tick回收孤立/过期/终止上传；取得锁才证明旧写入者已停止。冻结进程持续持锁，由受信运维处理，C不取得宿主控制权限。禁止仅凭时间、lease、PID或boot ID清理。删除/锁故障保持预留并暴露安全错误码。任何版本引用或sealed回指保护永久原件；封存重放仅清接收lease。

不支持独立宿主目录或未经验证的网络FS；A必须核验所有API实例使用同物理私有卷和锁命名空间。

## 纯解析CLI和ParseRunner

CLI：`python -m content.cli --input <任务只读输入> --format pdf|pptx|docx|txt|text [--encoding utf-8|gb18030]`。路径只由受信适配器分配，不接受HTTP任意路径。stdout为一个labconnect.parse/1 JSON；失败只给安全error_code，不带正文、路径或密钥。

支持位置文字预览：PDF页、PPTX幻灯片、DOCX/TXT段落，position从1开始保留空页/段编号；8192字符分片有part序号/ordinal/hash。正文2M字符、20k块、单输出16MiB。扫描/无文本NO_TEXT；不OCR、不Office转换。TXT仅UTF8/BOM、UTF16BOM或显式GB18030；OOXML读取前/实际读取有解压大小、条目数、比率、路径、宏和DTD限制，不extractall。PDF500页、PPTX300页。

ParseTask携带持久execution_id、job/generation/version/input_sha256/format/encoding，输入是授权字节AsyncIterator，不是任意宿主路径/命令。A start必须完整接收/核对字节后启动，返回前不留下消费迭代器的后台任务。同ID同绑定幂等，异绑定拒绝。start响应丢失用原ID inspect，不新ID重启。

能力和真实沙箱必须同时符合：固定sha256镜像、非root、只读根、无网络、仅本任务只读输入与受限临时区、环境白名单、无宿主/容器socket、跨实例单执行、可靠stop；内存384MiB、CPU1、临时64MiB、pids64、墙钟60秒、stdout16MiB、stderr64KiB。能力布尔声明不作为隔离证据。A实测网络/其他文件/密钥不可见及资源限制生效。

stop与start串行，对尚未开始ID也持久记录终止凭据，适配器重启和release后仍拒绝迟到start。stop确认整个执行单元停止；release确认任务输入副本/输出/临时区/执行单元清理，只此时返回true，重复幂等。绝不删除永久原件/快照。不能确认旧执行停止时阻止新重任务，普通查询/下载可用。

调度：每账号排队5、全局50、实际解析1。DB时间5秒心跳/20秒lease；后台重验User/LoginSession/School/RoleGrant/work_role及真实资源，校验会话归属/过期/撤销/临时密码。取消增generation，旧结果不能提交。失租约恢复不自动无限重试；显式retry新Job/真实新会话；成功重解析新Version。

## 候选HTTP和SDK要求

所有路径在`/api/v1/content`；typed DTO见schemas.py/views.py，除二进制流外均白名单响应。写命令须8–128字符Idempotency-Key；scope/creator/storage/role不接客户端注入。PATCH/决定/发布/停用用revision。q最多100字；普通列表limit50上限100、稳定排序；仅标题/文件名过滤，正文检索后包。

|类别|操作|
|---|---|
|库|GET/POST libraries；PATCH libraries/{id}；GET submit-targets|
|输入|POST materials/text；POST uploads；GET uploads/{id}；PUT uploads/{id}/bytes；POST uploads/{id}/cancel|
|资料|GET materials；PATCH materials/{id}；GET materials/{id}/versions|
|固定版本|GET versions/{id}、/chunks、/download；POST versions/{id}/reparse|
|审核|GET/POST material-reviews；GET material-reviews/{id}；POST material-reviews/{id}/decision|
|发布|GET/POST material-publications；POST material-publications/{id}/retire|
|任务|GET jobs、jobs/{id}；POST jobs/{id}/cancel、/retry|
|状态|GET capabilities：storage_available/parser_available|

原始PUT application/octet-stream在候选OpenAPI明确binary body；下载binary response/Content-Length/attachment/nosniff/private,no-store。SDK不得把原件当JSON。下载响应前及每256KiB以独立短会话重新验权，撤权终止流使Content-Length不符；不夹带错误正文。下载前完整哈希/字节检查，不持DB连接进行文件/网络I/O。chunks每响应1MiB分页budget，next_ordinal继续，不悄悄截断定位。

当前runtime缺配置明确503；错误413/409/403/503/507有安全提示。稳定任务码在scheduler.SAFE_ERRORS及worker错误协议；无原始异常栈/路径/凭据入公开响应。

## 当前检查及真实缺项

证据根`D:/codex/worktree/ffb2/SafeLabPlatform/others/reports/c-02/`，忽略，不提交真实输入/日志配置。

- 业务纯检查40项通过，日志backend-pure-tests.txt/exit=0。包括真实Windows独立进程锁、冻结/终止恢复、取消等待底层线程、同卷文件哈希/不覆盖、输入/结果/SQL编译/候选OpenAPI。
- worker可信合成测试15项通过、3项缺依赖跳过；verify退出1（parser.json、worker-tests.txt/exit）。因此四格式正常CLI及真实sandbox均未通过，不掩盖缺项。
- Ruff及git diff --check通过。model DDL编译不等于PG约束已生效，candidate OpenAPI不等于公共契约已发布。
- 已写真实PG服务3项、查询3项、数据库guard3项候选；未运行。A迁移发布后C继续补并实测五范围/双班/跨校/身份收窄、撤权和计数、审核拒绝/再提审、版本隔离、上传并发、配额竞争、文件-DB中断、迟到写入、双调度/失租约/旧结果、下载中途撤权等。
- 未启动C API/网页，无实际API origin或浏览器通过结论；未运行迁移、云模型或安装依赖。SQL guard候选仍待A真实PG审查/执行。

可重复命令（项目根PowerShell，shared_env真实检查需正常授权进程）：

```powershell
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
python .\others\scripts\shared_env.py backend unittest app.domains.content.tests.test_model_contract app.domains.content.tests.test_parse_runner app.domains.content.tests.test_validation app.domains.content.tests.test_upload_boundaries app.domains.content.tests.test_upload_fence app.domains.content.tests.test_parse_result app.domains.content.tests.test_scheduler_boundary app.domains.content.tests.test_query_contract -v
python .\others\scripts\shared_env.py backend ruff check app/domains/content D:/codex/worktree/ffb2/SafeLabPlatform/others/ai_worker/content
python .\others\scripts\shared_env.py worker content.verify --report D:/codex/worktree/ffb2/SafeLabPlatform/others/reports/c-02/parser.json
# 仅A迁移发布后，串行专用测试库，不在M1执行：
python .\others\scripts\shared_env.py backend pytest app/domains/content/tests -q --tb=short
git diff --check
```

## M2/M3及D/原生交接边界

C等待A公布公共技术SHA后同步，真实PG/HTTP/受限解析通过后才用生成SDK实现`web/src/features/content/`组件和独立真实API夹具。继承公共会话，身份/服务/退出变更清列表、预览、Blob、上传、旧响应；不localStorage持久正文/token/文件。加载/空/离线/无权限/未配置/失败/重试均有真实状态。

UI沿已批准蓝绿规范与公共组件，网页1440/390、键盘/触屏、恶意正文文字显示、真实选文件/知识点/审核发布/学生预览/下载哈希/取消重试/身份竞态取证。C不抢D入口或公共测试配置。

给D：PageRegistration候选、资料库/资料/上传/知识点/版本预览/审核/任务组件及来源定位协议。给A：downloadMaterial/openCitation和原生选择/保存所需固定版本、页段定位、二进制头与错误状态。具体前端导出在M3补完整。

D正式导航、Windows/Android原生保存、正式安装包、B2和公开云部署均后续独立待验，不作为C02的冒充结果。C自测不替代A接收或G独立验收。M3达成且本地提交/证据完整后，C停工。
