# C02/C1 云端更新与 A 主验收：2026-10-26

**已部署并由A主接收。** 统一服务地址为 [https://8.139.253.87](https://8.139.253.87)，实际云端源码 `cd1a385fe69b9f97e8f8ceaa84e84e542c4e76eb`、契约 `0.5.0`、迁移 `c1d0c000001`；该源码已推送origin/main并经ls-remote核对。后续验收文档提交不改变已部署镜像/源码，不冒称服务器已部署文档HEAD。Windows/安卓在现有“服务连接设置”使用同一HTTPS根地址；账号继续使用本机忽略区 `others/runtime/cloud-ecs/secrets/accounts.json` 中的现行凭据，不提交口令。

## 本轮逐项结论

| 用户要求 | 当前验收结果 |
| --- | --- |
| A副1接C02后端/worker、迁移/角色/运行器/真实API/SDK | 已接收；本机四格式及停止/锁/清理等历史证据保留，见[c02接收](c02-main-reception.md)；本次云端另验TXT与CSV正常闭环 |
| D1资料管理/授权搜索/定位预览/原件下载 | 正式网页真实流程已接收，见[资料页接收](material-ui-main-reception.md)；Windows/安卓登录与正文访问通过，原生持久保存仍未验 |
| C1→A副2→A接收，B2固定版本/安全DTO/受控答案依赖 | 已完成，见[C1接收](c1-main-reception.md)与[消费者基线](c1-consumer-baseline.md)；B2/D2/C2仍须用户手动首次启动 |
| GitHub及现有ECS更新 | cd1部署源码已推送且在原实例运行；本页记录真实云端验证，未标为完整A2/checkpoint-2 |

C02整包继续保留“原生保存未验”的未完成边界；不要求C回来收尾。专业60题/六关、完整考试/助手界面、G独立验收、物理安卓与Windows可见交互均不由本轮宣布完成。

## M2 实际部署与数据保留

A实际发送完整cd1执行SHA后，A副从干净primary/main构建并部署；无源码修复或部署重试。发布包395745280字节，SHA256 `7ccedaeb704b8d6874a08aeb76a77b7d6e4b8562ea45d4d7dadfd58e72fd7bf0`，5个镜像及10项包内校验全部匹配。原实例、PG容器/卷 `labconnect_cloud_pg18`、资料/证书卷保持，未采购新资源或调用付费AI。

- 原库15表/114行，其中14业务表含ID的全部行摘要在停写、兼容迁移前后保持。原账号ID/密码和课程实际继续使用；bootstrap返回created=false、password_reset=false，没有复制本机库或seed。
- 更新前备份 `/opt/labconnect/backups/20261026T112206Z-before-cd1a385fe69b9f97e8f8ceaa84e84e542c4e76eb.dump`，52826字节，SHA256 `b40c9a9fd6c57a75b681677ec4394cc589bbe65a91944adfd2794e0bf8b636cc`；A主独立核对大小、hash及pg_restore --list。未执行实际还原，不声称完整灾难恢复。
- 原JWT、AI主密钥、账号密码、CORS、ASR配置保持；仅有意替换API的数据库连接。owner只供迁移管理，实际API随机运行角色无super/create/bypass/表owner及owner成员权限。
- 私有controller Unix socket与固定解析镜像实际可用。API/DB/controller均无宿主端口映射，Web发布80/443；没有新增数据库公网规则、端口扫描或高级压力测试。
- 原本机.env、18767控制身份/配置、两套共享环境与模型/ASR配置指纹保持。云部署期间未重启本机服务；后续只允许A指定文档SHA的本机API/Web身份刷新，不重做迁移、构建或云部署。

## 真实业务与三端结果

标准证书校验的HTTPS、实际源码/镜像、0.5.0/c1迁移及内容能力通过；生产dev/identity、OpenAPI、docs/redoc为404。A主独立请求health/build-info、核对运行角色/socket及无内部端口映射。

云端研发合成TXT上传—实际解析—审核发布—授权正文检索/页段预览—原件下载hash一致；CSV导入预检/确认—审核发布—固定导出回读一致。固定QuestionVersion/LessonVersion的私有受控快照、学生安全投影及学生私有端点403通过。3条真实执行已停止/released，预留为0。样例只用于软件验证，不冒充专业审核或自动发布60题/六关；云样例ID见报告，不与本机样例混用或写死客户端。

| 客户端 | 实际来源与验证 |
| --- | --- |
| 云网页 | cd1/0.5.0，真实学生登录与云端资料正文加载 |
| Windows | 既有bae3461测试包，隐藏DOM验证，同一HTTPS登录/正文通过；可见窗口交互及持久保存未验 |
| 安卓 | 既有bae3461 debug APK，项目模拟器emulator-5556，同一HTTPS登录/正文通过；实体机及持久保存未验 |

既有原生包源 `bae3461a0e4cba9f6de8b13d12899a965a66b77b`，与云网页产品指纹同为 `21c7ce18604bc8ad2cf0a84fe56ac53f1dfb1dd61eb8485fd2a4d6361357120c`，契约0.5.0。A主核对EXE/APK/app.asar实际hash保持；本次工具修改不影响产品代码，未重建原生包，也不把它们称为cd1产物。Windows分发携带整个 `desktop/release/win-unpacked/`，安卓包在 `android/native/app/build/outputs/apk/debug/app-debug.apk`。

安卓首轮测试把地址预置到另一WebView来源，当前http://localhost实际service为空而使用本机默认地址，云账号登录被拒。失败/截图保留；仅安卓经产品“服务连接设置”切至同一HTTPS后复核通过，无产品代码修改。网页与Windows首轮成功保留，不把所有历史运行改称成功。

## 证据与接棒

静态清单位于A副树 `D:/codex/worktree/0aed/SafeLabPlatform/others/reports/cloud-c1-release/m2/manifest.json`，SHA256 `4e9247aeeff376ad168b77dc27e2ea38661943a79fd1cbb4088a96b58a5aaeb5`。A主核对21附件与10个cd1源码Git blob全部匹配，查看网页/安卓原生正文截图，回执在主树忽略区 `others/reports/cloud-c1-release-main/m2-receipt.json`；bundle独立回执同目录。原始数据与凭据不进Git，仓库保留本页及相关实现。

服务器deployment.json的normal_content_flow_verified=false是能力探针明确限定的输出；真实业务闭环另见cloud-flow.json、clients.json及上述静态清单，不混为同一检查。原备份实际恢复、文件/密钥完整备份、完整ASR采集问答、原生持久保存与G独立验收仍未完成。ASR/AI原配置保留，本轮未做付费AI调用或识别模型更新。

A副M2交接保存在系统Temp的 `labconnect-cloud-m2-cd1a385-handoff.md`。后续B2/D2/C2依[消费者基线](c1-consumer-baseline.md)手动首次启动；云更新本身不启动它们。

## M1 接收历史

执行者A副 / codex/a-executor，按 `cloud-c1-release`、规则发布 `b94cfb52664d0c3c480740ebb9106dc8c6997184` 普通续办M1。M1候选 `03081a1e54e4795677059b7e8aea78d38619f5ec` 已由A接收；在M1结束时ECS仍是717e1d0/0.3.2/b1迁移，尚无服务器写操作。A已独立核对10个附件与16个源码Git blob全部匹配，并复跑7项工具QA通过；清单SHA256 `c21d0c45e0b76b259a5d04e38fdc22f679b59928059790244839157684a1d393`。A实际发送第二个完整main SHA后才进入M2；实际云版本和普通业务流结果以随后封存的独立报告及受校验HTTPS为准，不能仅凭工具接收宣布部署通过。

## 实现与来源

cloud.py复用主线干净校验、SSH/known_hosts、公开bundle/SHA256SUMS。包包含API/Web/PG、固定14包parser镜像和独立受信controller镜像，带各自镜像ID/源码/锁/闭包/许可清单。parser `cloud` profile严格真实primary/main及固定共享worker，只写对应release忽略目录；缓存读取核对锁hash，许可只读，不改本机控制身份或共享依赖。

controller使用现解析器相同的固定Python3.13.16镜像和官方DockerCLI29.9.2 linux/amd64镜像；固定digest、上游源码及LICENSE/NOTICE哈希见 `others/deploy/cloud/images.lock.json`、`others/licenses/cloud-controller/manifest.json`。仅复制Docker客户端二进制，无daemon/buildx/compose插件；控制闭包只有标准库模块和空包初始化，无SQLModel/业务配置/DB或AI密钥/模型。基础镜像和许可校验不一致时停止。

compose管理controller生命周期，只有受信控制层挂Docker socket；API/解析作业无此权限。临时任务root与宿主路径相同，私有Unix socket/客户端配置目录及gid10001与服务端配置、journal分离。controller以CHOWN/DAC_OVERRIDE读取并清理uid65532输出；这只作用于可信控制层，解析作业原限制不降低。root容器不接业务/owner环境。真实Linux socket/任务闭环在M2核验。

## 凭据、数据与生命周期

原owner连接只给migration.env及一次性管理进程。`content_setup.py`从旧配置保留owner，持久化随机非owner角色及独立密码，重复部署复用；API只替换DATABASE_URL，其余JWT/CORS/原密码和AI/ASR配置保留。角色权限、owner成员关系/表所有权拒绝及必要DML/函数授权复用既有策略。管理脚本错误只打印脱敏类型/本工具错误，不输出可能包含CREATE ROLE密码的驱动异常SQL。

release继续独占锁、原库自定义备份/可读目录校验/hash、兼容静态迁移和成功后current切换。停写后对旧表全部行（含ID字段）排序做摘要，迁移后比较；不重建/seed/复制本机库，不重置账号/密码。已有controller先确认实际停止释放，配置更新检查所有旧journal停止/released，保留key/instance和历史；未知状态直接停止。bootstrap依旧幂等。

verify检查明确预期SHA、0.5.0/c1d0c000001、实际镜像/来源、原非owner、内容运行能力及Unix socket，同时保持公网DB/API/控制不映射、生产开发文档关闭。验证记录将普通业务流与能力分开，不能仅health正常就宣称TXT/CSV链路可用。

## 检查与接棒

M1范围为小型配置/角色工具QA、Python/Bash/compose解析和固定controller解释器/CLI导入；合成配置不接真实DB，Windows文件权限仅桩，不冒充Linux部署。M2按包从收到的真实main执行：原云库/凭据/卷/备份、部署、实际HTTPS/TXT/CSV/固定Q-L/学生安全投影、既有bae原生包连接同一HTTPS的基本登录与资料正文。若产品指纹不变，不重建无关Windows/APK，也不将旧包记为新源码产物。

本机C02四格式/锁/停止清理、D1网页下载、C1/T2/P2已接收证据保留，不重跑高级压力/全矩阵。Windows持久保存/物理安卓、题库考试/助手UI、G独立验收和新模块首次启动仍单列；M1当时只交工具候选，未执行ECS修改，M2结果见本页上文。
