# ECS 云端联调交接：2026-10-22

A / main 本轮从已集成版本部署，保留本地数据库、配置与开发入口。此交接只确认现有账号/课程及权限底座在云端可运行；当前仍按 D-UI → B 展示迁移 → D 整合 → A/F 既有 UI 验收顺序推进，C/B2 尚未放行。

## 访问与版本

- 网页及统一服务根地址：[https://8.139.253.87](https://8.139.253.87)。Windows、安卓在“服务连接设置”输入同一地址。
- 已部署网页/API、重建 Windows 测试包和 Android 调试 APK 的源码：`a1fb8e756886ef3c16e228a833de20d3c382fc76`；契约 `0.3.1`，迁移 `b1c0e0a00001`。后续部署工具、文档或静态设计提交另按 Git 记录，不冒充已运行功能。
- Windows：`desktop/release/win-unpacked/LabConnect.exe`，分发时携带整个 win-unpacked 目录；安卓：`android/native/app/build/outputs/apk/debug/app-debug.apk`。均为当前测试产物，正式安装器/签名另由 F 完成。
- 本机云端运维和四个合成测试账号仅存忽略的 `others/runtime/cloud-ecs/secrets/accounts.json`。使用各项当前 `password` 字段；`initial_password` 是历史首次凭据。不要提交或公开此文件。合成学校为 cloud-demo-a/b，当前页面不是完整 A2 工作台。

## 实际验证

实例 i-bp1hfqjc4ki4jcqwv6rn，杭州；SSH 核验 Ubuntu 22.04.5 LTS、2 CPU、约 3.5 GiB 可见内存、Docker 29.9.2、Compose 5.6.1，系统盘部署后约 31 GiB 可用。使用项目专用 SSH key 和经用户独立确认的主机指纹；未安装 Workbench CLI，未收集云 AccessKey。

标准证书校验通过，TLS 1.3，证书包含实际公网 IP，Caddy 持久化 ACME 证书并自动续期。当前证书有效期到 2026-10-28 09:41:41 UTC；自动续期的下一次执行尚未到期验证。

| 表面 | 本轮真实结果 |
| --- | --- |
| HTTPS API | 更新后 28 次请求通过：现有凭据/合成数据保留、三角色身份、课程与名单、跨学校拒绝、学生越权拒绝、退出撤销；首次初始化和改密在首次部署时完成 |
| 网页 | 1440px、390px 各三种身份，登录、同一授权课程与退出，共 6 组通过 |
| Windows | 重建的 LabConnect.exe 实际进程，独立测试 profile，三种身份通过；隐藏窗口以真实 DOM/API 验证，无隐藏窗口截图结论 |
| Android | 重建 APK 安装到 SafeLab_API36 / emulator-5556，真实 WebView 三种身份通过；补查发现一次模拟器 System UI 无响应提示，处理后确认前台无阻挡并以实际原生触控退出；保留前后设备截图，未测试实体手机 |
| 网络与隔离 | 公网 22/80/443 可达，5432/55432/8000/3389 实测不可达；数据库/API 无宿主端口映射；仅 Web 发布 80/443 |
| 访问控制 | 客户端合法来源预检 200，非许可来源 400；开发身份及文档页 404；API 非 root、只读文件系统和禁止提权；SSH 密码及交互密码认证实际已关闭 |

测试输入全部为合成资料，没有上传本地真实数据、参考 PPT、AI 密钥或监控媒体，没有调用模型或新增付费资源。原安全组仍有公网 SSH22、RDP3389 规则；3389 无服务监听，规则本身尚未删除。建议操作者在保留 Workbench 可用入口后收窄 SSH 来源、移除不需要的 RDP 规则。

可复核证据在本机忽略的 `others/reports/cloud-ecs/`：`api-smoke.json`、`client-smoke.json`、`security-check.json`、`deployment.json` 和截图。重复验证可能更新合成数据时间，不复制本地演示库。

## 更新与未完成项

完整操作见[部署流程](../deploy/cloud/README.md)。A 先提交并保持 main 干净，再运行 cloud.py build → deploy 实际 bundle → verify 同一地址；verify 以标准 HTTPS、容器标签和实际 API 版本共同确认，成功后更新服务器 deployment.json。已有凭据、文件卷、数据库卷和证书卷保留；更新前自动备份并迁移。

本轮手工备份 `/opt/labconnect/backups/20261021T204209Z-before-manual.dump` 已通过 pg_restore 清单与 SHA256 校验，更新前备份也保留。当前没有隔离恢复演练、文件卷完整备份或自动无损回滚结论。日后迁移实例须另外备份文件和密钥，不能只复制数据库备份。

试用余额、剩余小时和当月流量未从控制台核对；按用户提供的权益使用当前实例，不采购新服务。完整新 UI、助手历史/语音、考试、监控、正式客户端发布继续依各自阶段验收，本次基础云端验收不替代这些工作。
