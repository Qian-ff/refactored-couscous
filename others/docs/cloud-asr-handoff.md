# 云端 API / ASR 接入前置

A维护基础设施与内部适配；C接内容、助手和学校配置业务。当前实现已通过本地真实ASR的19项检查、4项worker回归、92项PG/API回归及契约/类型检查；云端部署与验收完成后在本文登记证据并另行放行C。当前不是完整助手交付。

## 启动和验收

主树A保留独立Python3.13与固定Paraformer缓存，业务API仍使用Python3.14。没有新依赖、系统服务或付费资源。SSH沿用项目known_hosts及专用key；服务器允许StreamLocal转发的实测结果已核对，保持GatewayPorts=no。

首次准备及更新只由A在干净main执行：

~~~powershell
python others/scripts/cloud_asr.py prepare
python others/scripts/cloud.py provision-ai
. ./others/scripts/Use-ProjectEnvironment.ps1
python others/scripts/cloud.py build
python others/scripts/cloud.py deploy "本次build输出的bundle.tar绝对路径"
python others/scripts/cloud.py verify https://8.139.253.87
python others/scripts/cloud.py probe-ai
python others/scripts/cloud_asr.py start
python others/scripts/cloud_asr.py verify
python others/scripts/cloud_asr.py verify --local-only
~~~

后续双击根目录Start-CloudASR.cmd恢复已配置的worker/私有通道，Stop-CloudASR.cmd停止。`cloud_asr.py status`核对本机及API容器端的来源、实例与模型；旧源码、模式不一致或云端通道失效时保留状态并失败，先stop再start，不接管无关进程。仅本地开发可用start --local-only；切云端前需stop。没有自动加入开机启动或唤醒其他聊天。

更新API沿用[云部署](../deploy/cloud/README.md)：不可变源码包、镜像摘要、更新前PG备份、迁移、健康与可信HTTPS。API不依赖worker才能启动；模型节点或隧道离线不阻断账号、课程等常规功能。

## 私有链路和数据

API容器 → 只读挂载的Unix套接字 → SSH加密反向通道 → 本机127.0.0.1:18765 → 独立ASR子进程。云端没有ASR TCP监听；数据库/API继续没有宿主端口映射。仅增加项目目录挂载，不修改系统SSH配置、防火墙或安全组。

本地忽略目录others/runtime/cloud-asr保存service.key、worker/client配置、进程状态及无正文日志，Windows ACL限当前用户。云端shared/asr中独立key、配置与套接字限API用户10001访问；会话独占锁，退出清理本人socket/活动配置，不删除其他会话。录音只经内存/管道处理；没有音频临时文件。成功、取消、超时后删除结果；断线未能主动删除时，子进程最长30秒、内存结果TTL60秒兜底，后台定时清理。

WAV上限30秒、964096字节，真实RIFF完整长度、16kHz/单声道/PCM16校验；最多一个推理子进程，忙时明确拒绝。每个任务独立子进程，取消/超时杀进程并回收；默认15秒，调用方可缩短。原始请求、音频、识别文字与密钥不写服务日志。

平台Flash配置先以独立云端主密钥重新封装，再上传密文；不上传本地主密钥或改动本地配置。provision-ai只允许首次配置/同revision保留，拒绝静默替换其他启用版本。probe-ai仅官方Flash、合成输入、最多1次新请求/输出128token，禁止重定向/自动重试/充值；成功重复运行读已保存结果，不再次扣请求。学校选择及审核/启用仍归C，未选择学校保持unconfigured；正式Pro尚未验证。

## C消费边界

内部Python适配为app.core.asr_client.AsrClient.from_environment()，提供health、submit、result、cancel及transcribe(audio, timeout_seconds=15, cancelled=回调)。配置由A控制，C不从HTTP输入接受worker地址/路径/key。客户端和学校管理员看不到此服务密钥。AsrError提供code/status，未配置或断线返回可识别状态；不得伪造识别成功或自动切换到另一个模型。

本机各角色树通过shared_env加载A的client.json及共享依赖，仍运行自己的业务源码；云端API通过LABCONNECT_ASR_CONFIG读取会话配置。A维护transport/、ASR适配、运维脚本及挂载；C继续拥有speech/、content/和助手领域，不复制本基础设施。

C在提交、执行、读取及返回结果各阶段验证学校/本人/课程/资料权限和账号级考试gate，将业务task ID映射到私有worker job ID。退出、撤权、关闭、切身份等通过取消/代次处理失效结果。B2未就绪时学生辅导保持不可用；用教师账号完成C业务验收。学校AI持久化/测试启用、教师资料问答、文字确认、TTS及D宿主仍由C/D接续。

本轮不注册公共ASR或助手业务HTTP，契约维持0.3.2，无新迁移。公开中文样例识别不代表网页/Windows/安卓麦克风采集或完整问答/播报通过；后者在C/D交付后由A/F逐端实测。

## 实测登记

本地开发初检：19项通过，含真实中文识别、缺失/错误key、来源错配、过大/损坏/截断WAV、并发拒绝、取消、超时及清理。最终云端与停机/重连证据待本轮部署后补充；在完成前保持原C门禁。
