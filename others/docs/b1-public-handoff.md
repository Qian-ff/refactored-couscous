# B1 公共后端与 SDK 交接

2026-10-21，A/main 集成固定 B 提交 `6d863e85d4f4003317943af52e3fbeb492be2dd9`（含前置提案、领域实现、测试及版本断言修正）。本阶段发布真实契约 **0.3.0**，供 B 继续实现和联调页面；B1 完整页面、C/D 与 A2 尚未验收，不启动 C/D、不推送。

## 接口及兼容

- A 挂载 management_routes、class_routes、import_routes，集中注册 Major、EnrollmentRequest、AccountInvitation、CoreAuditEvent、CommandReceipt。
- 原 /auth/login、/auth/logout、/auth/me、/courses 的路径和 CoursePublic 字段集合保留；UserPublic 兼容增加资料、首次改密标志和 revision；旧 POST /courses 不强制增加字段或幂等头。
- 学校/学院/专业、账号/授权/改密/邀请、目录/班级/名单/协作/交接/审批/归档、CSV 预检提交及教师选择均是真实实现。教师选择接口限有权主教师/管理员，按关键词返回最小信息，不要求手填教师 UUID。
- B2 的考试状态和培训记录仅内部协议，无占位 HTTP 或 SDK。C 的内容和助手尚未接入。
- 新写操作按生成客户端要求传 Idempotency-Key，编辑带 revision。页面使用公共内存会话及 X-Work-Role，不另建 token。首次改密先读 /auth/me，再改密并重新登录。
- 公共输入校验错误保留 type/loc/msg，移除可能含密码/CSV 的 input/context；不回显秘密输入。

生成服务入口：AuthService（含 changePassword/registerAccount）、ManagementService、TeachingService、ImportsService，原 CoursesService 保留。具体方法与参数以 web/src/client 为准，SDK 不手改。

## 数据库

新增迁移 `b1c0e0a00001` 接续 `e24a0c0a0001`，未重复 A0 的 CourseCatalog 回填。旧行以服务器默认值保持启用、未归档、不强制首改、revision=1；旧学号/专业保留 NULL，不伪造资料。

迁移先检测旧多主教师冲突，再改表；冲突保留原记录和旧 revision。增加专业/组织复合外键与空父级约束、学校学号唯一、有效主教师部分唯一和申请索引，保留 role_family_guard。自动 downgrade 禁止，回退使用已验证备份。

others/scripts/migrate_database.py 在待升级时先 pg_dump、检查归档可读性，再迁移并核对 A0 九类身份/课程数据的原字段数量及哈希。一键入口复用此工具；health 同时核验数据库迁移版本，旧库不冒充就绪。

本机演示库已备份升级，旧账号/密码哈希/角色/目录/教学班/教师关系/选课/会话校验一致；报告在忽略的 others/reports/b1-public/database-migration.json。未重置账号或数据卷。

## 已完成检查

- 62 项真实 PostgreSQL/API 检查通过，包含 B 的业务与独立 HTTP 并发、A 的旧库升级/冲突保留/组织约束/挂载/输入脱敏/旧库不就绪，以及原回归。
- Ruff、前端类型检查、实际 OpenAPI/哈希/生成客户端一致检查通过。
- 演示库 Alembic check 未发现元数据漂移。
- 25项协作/环境检查通过。contracts.py已复用共享解释器并绑定当前树源码，实际从尚未同步的B树导出0.2.0，而非误读A的0.3.0，无需B自己的.venv。
- 固定提交后的网页、Windows、安卓均重新构建，实际APK及Windows包内的build-info与网页一致：源码feb081c6152e75d002febea348d2bc0ede0f2ada、契约0.3.0。产物大小及SHA256见忽略报告others/reports/b1-public/builds.json；壳包版本仍为0.1.0，Windows为未签名测试目录、安卓为debug APK。
- Open-B1-API实际启动通过；主树API与Vite的SHA、工作树、源码指纹及契约核对通过。网页7项兼容检查通过，报告/截图单独写入b1-public，A0证据保留。
- Windows包复制到独立运行目录后，真实登录、新建课程、另一网页账号同步读取及renderer关闭Node访问均通过；报告windows-test.json。隐藏窗口的Playwright截图曾超时，改用当前Electron自带capturePage保持隐藏完成截图，失败和测试适配记录在native-harness.json；未修改F的客户端源码。
- 安卓API36模拟器实际安装/启动本次APK，读取Windows新建课程、与网页双向新建/同步课程、原生触摸退出及学生范围/移动布局均通过，报告android-test.json及截图。首轮被模拟器System UI无响应对话框遮挡；只读确认焦点及实际Wait按钮后，复用已有恢复脚本，再完整重测通过，保留android-obstruction.png。本轮未测试实体设备、麦克风或语音业务。

B分支在固定6d863e8之后的邀请时区、异常CSV和页面增量尚未包含在本次主树集成中；B已保留这些提交并合并401f0ac，报告其最新代码64项真实PG/API及真实契约检查通过。这是B分支的结果，不替代主树62项的记录；后续完整B1交付仍需A审查集成。

## 一键入口与消费

Open-B1-API.cmd 启动实际 API 与原登录/课程页面，再打开 /docs，明确为后端联调入口；不冒称完整 B1 工作台或 Open-A2。原 Open-Web/Windows/Android/A1 继续使用公共启动器。

~~~powershell
python .\others\scripts\shared_env.py probe
python .\others\scripts\shared_env.py backend pytest -q
python .\others\scripts\contracts.py check
pnpm run check
powershell -NoProfile -ExecutionPolicy Bypass -File .\others\scripts\Start-B1Api.ps1 -NoOpen
~~~

B 先提交自己的未完成改动，再合并 A 公布的完整公共提交 SHA。依赖锁未变，不需要重建 Python 或另装依赖。沿用 B 所有权内的组件夹具与真实 API 联调，公共入口/路由交 D。发现业务问题由 B 修正提交，A 接后续增量；本次不覆盖 B 工作树或自动同步其未提交文件。

后续仍为 B1 完整交付 → C → B2 联合验证 → D → A2。公共代码标签为本地 b1-api-0.3.0；最终 SHA 见 A 发布消息，历史 a2-ready 不移动。

可重跑网页兼容检查：PowerShell先执行`$env:LABCONNECT_REPORT_STAGE='b1-public'`，再执行`pnpm run test:web`。原生测试复用现有测试脚本，只在忽略目录绑定本树根目录及本阶段报告位置；业务断言未删除。三端构建/运行证据属于兼容账号课程切片，不代表B1新管理页面、C/D模块或A2九组合验收完成。后续仅文档提交不改客户端代码，产物仍以builds.json记录的feb081c为准。
