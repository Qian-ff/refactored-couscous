# A0 公共底座与阶段交接

本轮角色 A / main，起点 dfd087dabe96f82f9bafccf2497dbb284d715a0e（a2-start）；兼容模型/身份提交3dad37a556922d0c71478d5db6fa5c339d9186ba，完整公共代码与任务书提交c7b858b14088b28639395f530a0791e6197633e6。最终a2-ready为此后仅补充交接记录的发布提交，完整SHA用git rev-parse a2-ready取得并见最终聊天报告。2026-10-21，阶段可交B1，不表示业务/A2完成。

## 已实现的公共底座

- CourseCatalog与course_id教学班兼容；迁移e24a0c0a0001逐班回填、跨校约束和原账号/课程切片可用。
- X-Work-Role、available/active/effective身份与逐请求撤权；teacher默认及学生互斥，统一写入锁/数据库触发器保护并发。
- 前端公共会话代次/取消/退出失败清本地、服务地址变更、401与服务器确认身份；PageProps/注册/关卡学生和教师预览/PlatformBridge声明，不提前实现业务和原生适配。
- API实际契约0.2.0，application.json为版本唯一源，真实OpenAPI及生成SDK同步；HashRouter依赖精确锁定、许可归档，实际路由交D。
- AES-GCM学校/版本绑定、掩码、显式学校选择及不可变配置快照原语；C接学校DB/测试启用管理/页面，D接路由。加密本地Flash默认配置/主密钥在忽略区。
- A/B/C/D端口和CORS，common-root合成账号读取，源码SHA/树哈希/内容指纹/契约验证，原启动器拒绝错误或旧服务。
- 项目内业务Python3.14.6与独立worker3.13.16；共享依赖/源码绑定/测试锁，D测试授权web/tests/d-learning/。完整四份Goal见[任务书入口](ai/README.md)。

## 实际检查

| 表面 | 结果及证据 |
|---|---|
| 真实PostgreSQL回归 | 33项通过；含旧库迁移同名双班/关联ID、跨校FK、工作身份收窄/多学院/撤权、学生并发互斥、CORS、配置加密隔离 |
| 演示库升级 | 迁移前已pg_dump备份；12课程/12教师关系/2选课升级前后数量与SHA256一致，others/reports/a0/demo-migration.json；之后浏览器另新建合成课程用于联调 |
| 业务及worker环境工具 | 24项协作/环境unittest通过，领域根夹具/进程锁及两树模块绑定/拒绝外部模块均检查 |
| 网页类型/构建 | 主树pnpm check与build:web通过，B/C/D均类型通过；build-info无本机路径，发布后构建元信息另存忽略证据 |
| 浏览器 | A/B/C/D各自5173/5174/5175/5176真实运行，每树7项共28项通过；common-root账号与两端源码身份均核实。覆盖登录新建/另账号同步、390px学生/退出、密码网络失败、会话旧请求/401隔离、撤销/新地址/退出失败、错误SHA/树/指纹/契约拒绝。会话单元使用合成网络响应，权限另有真实PG检查 |
| 原一键网页入口 | Start-A1 -Target Web -NoOpen实际启动API+PG+Vite成功；旧服务故意保留时被拒绝且未擅自停止，launcher-guard.json。随后仅重启本轮进程，已提交源码身份匹配 |
| Flash | 官方Flash真实2次HTTP200，连接+JSON业务字段校验，共128 token，others/reports/a0/provider.json；计数2/3，未调用Pro、不上传私密/真实数据 |
| CPU ASR | 真实5.614625秒中文示例通过，CPU识别约1.02秒；报告speech.json确认ORT1.28.2及worker内DLL。已精确补齐core1.13.8，未改系统；模型/代码/原生运行库许可已归档 |
| 容器 | labconnect-api:a0镜像已构建，实际生产导入0.2.0通过，/api/v1/dev/identity真实请求404；生产启动无需开发Git |
| SDK/准备与三树同步 | 真实OpenAPI/哈希/SDK一致，准备文件/链接/忽略检查通过。B/C/D干净快进到公共代码提交，版本0.2.0/所有权4、业务与worker源码绑定/类型均通过，依赖离线安装downloaded=0；最终发布记录提交继续快进并复核，状态存others/reports/a0/release.json |

## 可复现入口

~~~powershell
python .\others\scripts\check_preparation.py
python -m unittest discover -s .\others\qa -p "test_*.py" -v
python .\others\scripts\shared_env.py backend pytest -q --tb=short
python .\others\scripts\shared_env.py backend ruff check app tests
python .\others\scripts\contracts.py check
pnpm run check
pnpm run build:web
powershell -NoProfile -ExecutionPolicy Bypass -File .\others\scripts\Start-A1.ps1 -Target Web -NoOpen
pnpm run test:web
python .\others\scripts\shared_env.py probe-worker
~~~

重新下载/验证ASR用Prepare-Worker.ps1；不要重复执行provider_probe扩大计费，A0累计最多3次。其他真实AI调用待后续阶段按配置/额度执行，API不是永久免费。Pro当前实际请求名deepseek-v4-pro，正式学校自由配置支持模型。

## 运行边界与后续接收方

完整账号管理/目录CRUD/审批/搜索由B1；内容/题库/学校AI设置/问答/语音业务由C；考试/续答/进度/记录及C联合限制由B2；三角色路由/学习互动由D。设计的接口未加入OpenAPI，不以协议或声明冒充实现。

C可用教师完成真实问答/语音，B2状态未有时学生暂停；后续联合验收不构成C完成的循环前置。A2才做Open-A2、客户端重建、九组合和真实设备采集/引用下载；旧A1安装包未重建为A2，示例ASR不证明三端录音。完整监控/安装器分别E/F。

受限进程的路径警告已定位Windows卷路径查询权限，正常授权进程无此警告。只把运行时收回项目缓存，未隐藏stderr或修改系统/外部沙箱，见[共享环境](shared-environment.md)。非阻塞B1业务；需正常授权执行的本机网络/Node检查按环境处理。

A0结束仅本地提交与新a2-ready，不额外push，不移动a2-start/checkpoint-1。后续B1→C→B2→D各次公共集成交A；A2完整验收后才checkpoint-2已授权推送。本轮不自动启动其他聊天。

## 发布与开工核对

~~~powershell
git rev-parse a2-ready
python .\others\scripts\workflow.py status --baseline a2-ready
~~~

A/B/C/D应同一发布HEAD、clean/registered/contains_baseline/ownership_current为true，契约0.2.0、所有权4。旧任务树保留且未被冒称就绪。先复制[B任务书B1 Goal](ai/B-core.md#b1-goal)到原B聊天；本轮不自动启动它。C/B2/D使用各自完整Goal，等待A集成前序交付并公布新完整SHA，不再重复A0模型/加密/依赖工作。
