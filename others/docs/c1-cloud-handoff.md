# C02/C1云更新工具候选

执行者A副 / codex/a-executor，按 `cloud-c1-release`、规则发布 `b94cfb52664d0c3c480740ebb9106dc8c6997184` 普通续办M1。当前只完成分支部署工具；ECS在M1保持只读，仍是717e1d0/0.3.2/b1迁移。准确候选SHA及检查见本轮A副回执与独立 `others/reports/cloud-c1-release/m1/`。A接收并实际发送第二个完整main SHA后才进入M2构建/部署。

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

本机C02四格式/锁/停止清理、D1网页下载、C1/T2/P2已接收证据保留，不重跑高级压力/全矩阵。Windows持久保存/物理安卓、题库考试/助手UI、G独立验收和新模块首次启动仍单列；本工具候选没有放行它们，也未推送或执行ECS修改。
