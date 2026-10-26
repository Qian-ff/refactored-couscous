# C02/C1 已接收主线的 ECS 更新

编号 `cloud-c1-release`，2026-10-26。用户在A主明确要求核对首轮A副1/D1、C1→A副2→A接收，并提交GitHub和云端。本次是已有部署流程的普通接续，不自动首启B2/D2/C2、新原生或监控；gpt-6.1-sol / medium / Default。A主负责Git推送与main最终接收；A副只在登记分支提交候选，并按A实际发送的main SHA执行云构建/部署。

## 来源与当前状态

- 主线输入 `25fe60ce2a55a266d0b0f1152d4b32ef8909af79`，0.5.0/c1d0c000001；本机功能/三端产物源bae，相关证据见c1-main-reception及material-ui-main-reception。不重跑四格式/锁/取消清理的已封存全矩阵。Windows/安卓持久保存未验，C02整包不得因本次云更新伪标完成。
- ECS `i-bp1hfqjc4ki4jcqwv6rn` 已实际SSH核验：原api/web为717e1d0、0.3.2，原库labconnect/b1c0e0a00001、15表，原API仍owner；没有内容控制端或migration.env。原卷/证书/账号保持，空盘约26GiB，宿主Python3.10不支持当前asyncio.timeout。
- 只读报告 `C:/Users/lenovo/AppData/Local/Temp/labconnect-cloud-readiness-25fe-20261026.md`。现cloud.py/release.sh是可复用流程，但直接发布当前包会缺角色分离和内容运行器；先补工具、A接收后才实际部署。
- 规则执行SHA由A在本包提交后实际发送，A副先保留旧提交并普通合并；实际身份/树/分支、当前规范/模板、共享环境及具体委托均重新核对。

## M1：分支完成最小部署配套

1. 复用cloud.py的干净main校验、bundle/校验清单、SSH主机指纹、release锁、备份、兼容迁移和current切换，不建第二套发布器。API/Web继续精确源码标签；加入已验14包parser/transfer镜像、受信controller镜像和各自实际来源/内容/锁/许可hash。
2. 选择独立受信controller容器：复用当前固定Python3.13基础镜像，DockerCLI沿用现有29.9.2版本，从官方镜像/发行物固定digest和来源许可，不用浮动latest，不给宿主安装新Python或模型。控制镜像仅标准库控制闭包，不复制业务.env、SQLModel、AI/DB密钥或整个worker。仅受信控制层持有Docker操作权限；API与临时解析容器无Docker socket。没有批准使用普通API的privileged模式替代它。
3. Linux复用Unix socket、gid10001和现有固定三任务、真实停止/释放、单实例/journal。持久任务路径在controller和宿主Docker保持同一绝对路径；API只挂只读客户端配置/套接字目录及自己的资料卷，不挂服务端配置/journal。新旧控制实例/密钥/历史在重复更新时保留；切换前实际停止/清理，不清空任务记录掩盖失败。服务生命周期由项目compose管理，不改其他项目或Docker全局配置。
4. 从原owner连接准备独立migration.env及随机非owner运行角色；只替换API的数据库连接，原JWT/AI主密钥、密码、账号和CORS/ASR配置保留。原15表迁移前备份、hash及ID/内容摘要，升级接收的静态迁移并授必要DML/schema/sequence/function权限。API不能成为owner或owner成员；迁移owner不挂载到API、controller或任务。重复运行不换密钥、不重置密码、不seed/复制本机库，不删除原卷。
5. parser准备需最小纯构建路径：复用现有精确锁、14包闭包/官方wheel缓存和只读许可核验；云构建只写自己的忽略目录，不重写本机18767配置/image.json或共享环境，不为云端复制Windows venv。保持原main/候选守卫，不添加任意目录/命令旁路。
6. verify增加实际预期SHA、0.5.0/c1d0c000001、镜像/容器来源、非owner和内容控制能力核对，不能只health正常就声称内容可用。生产dev/identity/OpenAPI文档入口继续404；Caddy已有精确上传例外复用，不开放数据库/API/控制端公网端口。
7. 只做相关小型包/角色配置工具QA、Python/Bash/compose解析及controller固定解释器/CLI导入检查；不重跑旧高级安全/压力/崩溃矩阵。controller/Unix socket首次真实服务闭环放在M2的同一ECS验证，避免用Windows路径伪装Linux证明。

M1在A副树本地提交，交A完整SHA、差异、检查、镜像来源/digest/许可和未跑项。**A接收并实际发送第二个完整main执行SHA之前，禁止云端上传/改配置/建角色/迁移/启停。** 只读SSH可继续，密钥/凭据/完整容器Env不输出。

## M2：准确main构建与真实云更新

收到A实际接收的main SHA后，在真实primary/main干净源码构建bundle并核对清单，只生成忽略产物。新增部署工具不改变产品API/Web源码指纹时，既有bae原生包可复用并明确记录来源；云网页重新生产构建，不要求无影响的Windows/APK重复重建。不得把旧原生包记录成新SHA构建。

先核对部署实例/current/原卷/原15表与凭据，再取得发布锁、停写、备份并校验，准备角色/私有配置、兼容迁移、启动受信控制服务及API/Web。保留原库/文件卷/证书/ASR/配置，避免重复prepare生成新密码；本机开发服务/库/18767/ASR/模型与共享venv均不改。失败保留原目录、备份和错误，按实际阶段处理；不删除卷、不强退数据库掩盖迁移。

普通真实验证：标准HTTPS及确切源码/契约/迁移、原合成账号/课程保留、API非owner、控制源码/镜像和Unix socket、一个TXT上传解析—审核发布—授权检索/正文预览—原件下载hash、一个CSV/C1固定题目关卡/受控快照及学生安全投影。云合成样例明确标注，专业60题/六关不自动发布；不复制本机数据充数，不调用付费AI。

验证网页与既有Windows包/安卓模拟器接同一HTTPS后端的基本登录/资料正文访问。Windows隐藏DOM/可见窗口、模拟器/物理机及实际下载字节/持久保存分别报告；不能以网页或构建成功替代原生实证。基础公网检查仅确认DB/API/控制端未映射/未公开，保留SSH管理通道，不做端口扫描或高级压力测试。

报告在独立 `others/reports/cloud-c1-release/`，活动日志先写runtime再封存；记录bundle/source与各镜像来源、备份/旧表摘要/凭据不变、实际权限/路径、原生包来源和真实结果、失败/未验。源码修复仍在A副分支提交交A接收后重建发布，不直接编辑main跟踪文件。无差异不空提交。

## 授权与结束

用户本次直接授权A推送现有main并更新既有ECS，取代本轮早先“非checkpoint不推送/不部署”的限制；不把这次备份推送标作完整A2 checkpoint-2，不覆盖历史标签。A副不push、不派活。不得采购新付费资源、升级实例或改计费方式；仍用原2核4GiB实例和现有缓存。

A最终核对云版本与验证证据，更新逐项任务状态/云交接并保存GitHub实际SHA。C02原生持久保存、实体设备、完整题库考试/助手界面、G独立验收及后续新模块门禁继续单列。普通已知局部问题最多修复复查三轮，关键范围外问题集中交A；结束按handoff保存系统Temp。

## 2026-10-26 实际接收与最后身份刷新

M1候选03081a1已接收为main `cd1a385fe69b9f97e8f8ceaa84e84e542c4e76eb`；A已push且ls-remote核对同SHA，再实际派发M2。M2已在原ECS完成，无源码修复/部署重试，A接收结果见[c1-cloud-handoff](../c1-cloud-handoff.md)。原库14业务表全行摘要、原账号/配置保持；0.5.0/c1迁移、TXT/CSV/固定Q-L/学生投影及三端同一HTTPS通过。原生包继续使用bae源；持久保存/物理机等未验项保留，未启动下一模块。

本包功能工作结束。A在本轮验收文档提交后可实际发送该完整SHA，授权A副仅刷新确认归属main的本机API8000/Web5173启动身份：先核验PID、启动时间、命令和旧来源，确认产品指纹相同；结束核对identity/health。只重启本项目明确归属的这两个开发服务，不改本机DB/数据/配置、控制18767、共享venv、ASR/模型、原生产物或ECS；不重新迁移/构建/云部署。无跟踪差异不空提交，完成后Temp交接并待命。它是本次普通验收收尾，不是恢复旧Goal或新模块首次启动。
