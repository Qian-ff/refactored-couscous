# ECS 云端联调交接

**2026-10-26当前版本已更新为0.5.0，迁移c1d0c000001，实际源码 `cd1a385fe69b9f97e8f8ceaa84e84e542c4e76eb`。** 访问 [https://8.139.253.87](https://8.139.253.87)；原云库、凭据、PG/文件/证书卷保持，TXT/CSV/固定内容及三端同一HTTPS基本访问通过。完整结果、备份、来源与未验边界以[C02/C1云端接收](c1-cloud-handoff.md)为准。以下2026-10-23记录保留历史原义，旧源码/产物/证书日期不代表当前部署；原生持久保存仍未验，B2/D2/C2未自动启动。

## 2026-10-23 历史接收

A / main 从已集成版本更新云端，保留本地数据库、配置与开发入口。既有UI及[API/ASR接入前置](cloud-asr-handoff.md)已验收，c-start-ready允许C开工；B2仍等C交付后另行放行。当前只确认现有账号/课程及私有识别基础设施可运行，完整助手业务仍由C/D接续。

## 访问与版本

- 网页及统一服务根地址：[https://8.139.253.87](https://8.139.253.87)。Windows、安卓在“服务连接设置”输入同一地址。
- 已部署网页/API源码：`717e1d0e5f88071c52b361cf3fa1c3bb09d13697`；契约 `0.3.2`，迁移 `b1c0e0a00001`。后续工具/交接/门禁提交另按Git记录，不冒充已部署源码。旧a1fb8e7/0.3.1保留历史记录。
- Windows与Android复用existing-ui-accepted=`5a4d4fa7fe850a8e16391130cc04b0473cacdde8`的已验收测试产物，本轮未改共享界面/原生代码或重建包；两包前端内容指纹与云端同为4b21a41bfb7a06079a73ef7bfef04b6bb5115384d76129852a50c42e89fcc2a2。
- Windows：`desktop/release/win-unpacked/LabConnect.exe`，分发时携带整个 win-unpacked 目录；安卓：`android/native/app/build/outputs/apk/debug/app-debug.apk`。均为当前测试产物，正式安装器/签名另由 F 完成。
- 本机云端运维和四个合成测试账号仅存忽略的 `others/runtime/cloud-ecs/secrets/accounts.json`。使用各项当前 `password` 字段；`initial_password` 是历史首次凭据。不要提交或公开此文件。合成学校为 cloud-demo-a/b，当前页面不是完整 A2 工作台。

## 实际验证

实例 i-bp1hfqjc4ki4jcqwv6rn，杭州；SSH核验Ubuntu22.04.5 LTS、2 CPU、约3.5GiB可见内存、Docker29.9.2、Compose5.6.1，系统盘更新后约30GiB可用。使用项目专用SSH key及经用户独立确认的主机指纹；未安装Workbench CLI，未收集云AccessKey。

标准证书校验通过，TLS 1.3，证书包含实际公网 IP，Caddy 持久化 ACME 证书并自动续期。当前证书有效期到 2026-10-28 09:41:41 UTC；自动续期的下一次执行尚未到期验证。

| 表面 | 本轮真实结果 |
| --- | --- |
| HTTPS API | 36项请求通过：现有凭据/合成数据保留、4个合成账号、三角色身份与本人班级关系、跨学校拒绝、学生越权拒绝、退出撤销；首次初始化和改密在首次部署时完成 |
| 网页 | 1440px、390px 各三种身份，登录、同一授权课程与退出，共 6 组通过 |
| Windows | 已验收LabConnect.exe实际进程，独立测试profile，三种身份通过；隐藏窗口以真实DOM/API验证，无隐藏窗口截图结论 |
| Android | 已验收APK在SafeLab_API36 / emulator-5556，真实WebView三种身份通过并核对无原生阻挡；未测试实体手机 |
| ASR / AI | API容器→SSH私有套接字→本机CPU识别的19项检查、停机/超时/取消/清理及恢复通过；官方Flash真实JSON仅1次请求、59token；没有三端采集/完整问答结论 |
| 网络与隔离 | 公网22/80/443可达，5432/55432/8000/3389/18765实测不可达；数据库/API无宿主端口映射，云端无ASR TCP监听；仅Web发布80/443 |
| 访问控制 | 客户端合法来源预检 200，非许可来源 400；开发身份及文档页 404；API 非 root、只读文件系统和禁止提权；SSH 密码及交互密码认证实际已关闭 |

测试输入全部为合成资料及固定公开中文WAV。平台配置用独立云主密钥封装后只上传密文；没有上传本地主密钥、真实用户资料、参考PPT或监控媒体，没有新增付费资源。原安全组SSH22/RDP3389规则未改动，3389仍无监听；既有SSH认证限制保留。

本轮可复核证据在本机忽略的others/reports/cloud-asr/：access.json、clients.json、cloud/local-probe.json、fault-recovery.json、provider.json、server.json与截图；旧others/reports/cloud-ecs保留前次部署历史。本轮访问检查只读既有合成业务资料，不复制/重置本地或云端数据库。

## 更新与未完成项

完整操作见[部署流程](../deploy/cloud/README.md)。A 先提交并保持 main 干净，再运行 cloud.py build → deploy 实际 bundle → verify 同一地址；verify 以标准 HTTPS、容器标签和实际 API 版本共同确认，成功后更新服务器 deployment.json。已有凭据、文件卷、数据库卷和证书卷保留；更新前自动备份并迁移。

本轮更新前备份/opt/labconnect/backups/20261023T100555Z-before-717e1d0e5f88071c52b361cf3fa1c3bb09d13697.dump已通过pg_restore清单及SHA256校验，旧备份保留。当前没有隔离恢复演练、文件卷完整备份或自动无损回滚结论；迁移实例仍需另备份文件与独立密钥。

试用余额、剩余小时和当月流量未从控制台核对；按用户提供的权益使用当前实例，不采购新服务。ASR目前依赖本机在线，重启后用Start-CloudASR.cmd恢复。助手历史/三端语音、考试、监控和正式客户端发布继续按后续阶段验收。
