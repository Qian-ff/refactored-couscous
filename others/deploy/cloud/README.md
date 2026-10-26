# ECS 云端联调与演示

A维护本流程；2026-10-26已从干净main部署 `cd1a385fe69b9f97e8f8ceaa84e84e542c4e76eb`、0.5.0/c1d0c000001至 [https://8.139.253.87](https://8.139.253.87)，A已接收真实TXT/CSV/固定内容与三端基本连接结果，见[云端接收](../../docs/c1-cloud-handoff.md)。后续仍须从A接收的干净main及实际发送的执行SHA发布；文档HEAD不等于当前部署源码。D/B既有UI改版和后续门禁继续按[阶段入口](../../docs/a2-start.md)，不将本次部署称为完整A2验收。

## 连接和配置

本机已有Windows OpenSSH。首次通过用户已登录的网页Workbench为当前实例添加项目专用公钥，用户从Workbench确认服务器ED25519指纹；标准SSH返回同一指纹后才记入项目known_hosts。所有SSH/SCP均严格核验此记录，拒绝未知或更换的主机，不改全局SSH配置。

连接配置、私钥、known_hosts保存在忽略的others/runtime/cloud-ecs/access/。connection.json只含instance_id、region、host、user、port及host_fingerprint；实例详情和探测证据保存在忽略的others/reports/cloud-ecs/。密钥留本机，不贴入聊天或Git。

2026-10-22审查过阿里云官方Workbench install.ps1（下载SHA256 44e6933ec6acd9c511ae6c448b4f02e5abd2f4ef71081b7937cdfd99a047537a），未执行。该脚本写入Program Files并修改用户PATH；CLI另需云端AccessKey/STS等凭证。此项目采用已有SSH及网页首次授权，不为部署额外安装系统工具或创建云端长期AccessKey。

安全组对公网仅为Web开放TCP80/443，数据库和API不发布宿主端口。SSH22用于已授权运维，完成连接后可将来源收窄为操作者出口IP和实际Workbench来源。Linux不需要RDP3389。保留用户已有管理通道，调整前先确认新通道可用。

```powershell
python .\others\scripts\cloud.py probe
python .\others\scripts\cloud.py prepare
```

prepare只在本机忽略区生成全新的云端数据库密码、JWT密钥、32字节AI配置主密钥与首次运维密码，独立于根.env；Windows目录ACL限制当前用户。重复执行保留原凭据，部分配置缺失时停止，不静默换密钥。AI连接前置另见[ASR及加密平台配置交接](../../docs/cloud-asr-handoff.md)：仅上传独立云端主密钥封装的配置密文，不上传本地监控资料。

## 构建与发布

```powershell
git status --short
python .\others\scripts\cloud.py build
python .\others\scripts\cloud.py deploy "上一步输出的bundle.tar绝对路径"
python .\others\scripts\cloud.py status
python .\others\scripts\cloud.py verify https://实际公网IP或已配置域名 --source-sha 本次准确main完整SHA
```

build要求干净main，固定源码SHA及API/网页内容指纹，构建生产网页与非root后端镜像。基础镜像见[images.lock.json](images.lock.json)，依赖继续用pnpm-lock.yaml和uv.lock。包只含生产镜像、公开部署文件、版本及校验清单，无.env、真实账号、SSH密钥、私密PPT、设计树、虚拟环境或模型缓存。构建和上传在本机进行，减少2核4GiB服务器的构建压力。bundle.tar留忽略区，不进入Git。

服务器采用/opt/labconnect/shared、releases/完整SHA、incoming和backups。首次部署传入独立凭据；后续保留服务器凭据，避免重建密码导致数据库失联。Docker命名卷labconnect_cloud_pg18、labconnect_cloud_files、证书卷持久化，和本地safelab-a1卷完全独立。DB/API/Web/controller限额分别768/1024/256/128MiB，临时解析任务另有限额；限额不等于实测峰值，不在这台实例加载语音或视觉模型。

发布会核对压缩包和镜像清单，取得独占部署锁，启动数据库、停止本项目API/网页写入、导出并验证PostgreSQL自定义格式备份，再运行同版本Alembic迁移、首次运维初始化和健康检查。首次初始化只创建一个平台运维账号并强制改密；重复执行不重置密码，不调用生产环境禁止的app.seed。上次release及数据库卷保留；成功后current才切换。失败停止并保留备份、旧目录和错误信息，避免以删卷或强行回退数据库掩盖错误。

HTTPS使用官方Caddy、Let's Encrypt ACME shortlived证书，持久化证书并自动续期。官方已支持公网IP证书，需真实通过公网挑战；域名可后续替换。只有标准证书校验成功后才算公网HTTPS可用，不使用跳过证书检查或浏览器安全提示来冒充通过。

## 验证及客户端

网页和API共用HTTPS来源。生产网页自动用同源API；Windows/安卓在现有服务设置中输入同一HTTPS根地址，服务端统一鉴权。客户端只保存服务地址和个人设置，密码/会话按现有规则处理，不接触数据库凭据。

允许来源包含Windows固定http://127.0.0.1:48621、安卓WebView的localhost来源及已登记开发端口。已有云环境需要补齐客户端来源时，运行`python others/scripts/cloud.py sync-cors`；它只更新CORS并重建API容器，保留密码、密钥、数据及当前镜像版本。

每次发布核对公网health的契约/迁移、build-info.json的源码SHA、容器标签和实际BUILD，验证登录/首次改密/退出、未授权拒绝及学校范围；确认公网数据库端口不可达且宿主机无对应端口映射。无真实Windows/安卓运行证据时单独标为待验，不以网页或容器构建代替。生产不提供dev/identity；网关不开放开发文档页面。

初始运维登录信息仅见本机忽略的others/runtime/cloud-ecs/secrets/accounts.json；首次改密后记录实际新密码，bootstrap不会替换它。云端合成演示数据须明确标注，使用真实业务API创建，不复制本地数据库或使用已知演示密码。

## 备份、恢复与费用边界

0.5发布包增加固定parser/transfer镜像与独立受信controller镜像（Python3.13.16、DockerCLI29.9.2），镜像ID/锁/闭包/许可在清单。`prepare.py --profile cloud`只写该main SHA的cloud-ecs/releases目录，并复用核验过的官方wheel缓存，不修改本机18767的image/key/instance或共享环境。

仅controller持Docker socket，API和解析作业不持有。controller使用无网络容器、同宿主绝对路径的临时任务root、持久journal和私有Unix socket；客户端目录与服务端配置分开。原有ASR/AI目录及配置保留，不在云端安装宿主Python/语音模型。

首次C1更新从原owner连接准备独立migration.env，停写备份后记录旧表/ID/内容摘要，通过仅管理进程创建并验证随机非owner角色，只替换api.env的数据库连接；旧JWT/CORS/密码/AI主密钥/原库/卷/证书保持。迁移后授权并比较原数据，bootstrap仍幂等且不seed。上述数据/角色检查已在本次M2实过，旧14业务表全行摘要保持；后续更新仍须重新核对，不能复用旧报告冒充新部署验证。

更新已有内容控制服务时，先通过旧服务确认实际停止/release并停旧控制器，再核对journal和保留的key/instance切换。缺少身份或未确认执行直接失败保留；不清空历史。完整HTTPS/预期SHA/0.5.0/c1迁移、实际镜像和非owner/内容能力检查由verify完成；普通TXT/CSV/固定Q-L及客户端真实流程另记报告，能力探针不等同业务流验证。

```powershell
python .\others\scripts\cloud.py backup
```

数据库备份在服务器backups/，带SHA256，更新前自动保留。密钥另存shared并由本机忽略区保留；数据库备份不包含密钥和上传文件，完整灾难恢复须同时保留文件卷及独立密钥。当前只实现数据库备份与校验，尚不宣称文件备份、异机恢复演练或自动无损回滚完成。

需要恢复时先停止此项目API/网页、保留当前数据库另做备份，在隔离新库中pg_restore并运行同版本健康/数量校验，再由A切换；未经恢复校验不覆盖现有数据。旧API未必兼容新迁移，不仅回退镜像冒充数据库回滚。

不自动采购RDS、EIP、域名、负载均衡、OSS或付费证书。不调整实例规格、计费方式或试用权益。试用小时和20GB/月流量来自用户提供信息，剩余额度需控制台核实；后续新增付费资源先说明费用。日志有限额，旧版本、备份和镜像需按实际空间评估后管理，不自动删除已有数据。

来源：[Workbench CLI安装及凭证](https://help.aliyun.com/zh/ecs/user-guide/install-and-configure-workbench-cli-credentials)、[安全组Web案例](https://help.aliyun.com/zh/ecs/user-guide/security-groups-for-different-use-cases)、[Let's Encrypt公网IP证书](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)、[Caddy ACME配置](https://caddyserver.com/docs/caddyfile/directives/tls)。
