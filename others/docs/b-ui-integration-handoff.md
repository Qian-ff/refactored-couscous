# B-UI：A 集成与 D 二次整合交接

后续公共依赖已更新：D接续使用[student-relations-ready / 0.3.2](student-relations-handoff.md)，包含本页b-ui-integrated基线。本页0.3.1及运行证据属于B展示迁移当轮记录，不能当作新本人关系页面的验收。

B交付6682ec37a2543e9e50a1bf400a8d70057351c807，组件起点d-ui-components-ready为27c1e385d2e0b97ce5880e0230bae2be7aa1a5c1。A从452dd40233429b9dddb26bf1f940bacb3cefc4af合并，保留公共foundation表单内搜索补丁及全部分支历史；本轮验证后发布本地b-ui-integrated，完整提交用git rev-parse 'b-ui-integrated^{}'获取。旧标签不移动。

## 当前范围

B的17个文件均在admin/teaching范围，完成教师和管理员既有展示迁移。A独立核对SessionPage、useBusinessQuery、useBusinessAction函数文本与组件基线一致；后端、公共入口/路由、共享组件、依赖、API/SDK和冻结设计无B改动。契约仍0.3.1，迁移仍b1c0e0a00001，无数据库迁移或重置。

正式页面保留七条PageRegistration及courseId教学班参数。目录/班级各自搜索分页，桌面表格和手机RecordList使用同一份字段/动作；账号、组织和CSV使用完整长表单，危险操作包装原服务端命令。B的功能映射和原始证据见[完成交接](../../web/src/features/teaching/handoff/b-ui-completion.md)，D衔接见[页面README](../../web/src/features/teaching/README.md)。B仍唯一维护其ui.tsx/business.css和业务页面。

## 一键体验与运行证据

双击根Open-BUI.cmd进入正式网页；Open-UI及通用三端入口继续复用同一启动器。登录、连接设置和本机合成账号规则不变，本机与云端账号分别管理。

1. 教师在“课程与教学班”新建课程与首班；在目录索引选择或清空目录，在“有权访问的教学班”内独立搜索。进入班级查看设置、名单、审批和教师协作；交接/归档按真实权限确认。
2. 管理员在权限范围查询同一教学班；通过组织、账号和邀请入口操作已有功能。CSV从“批量导入账号/名单”分别进入，预检后整批提交；不确定结果使用原请求重试。
3. 手机展开导航和筛选，检查带标签记录与长抽屉；编辑冲突保留输入，明确重读后再保存。归档、撤权、失败、离线及未开放状态来自真实接口和会话。

A在主线重跑公共18项和B所属9项真实浏览器场景，检查生产资源，并重建Windows/安卓后进行三角色运行验证。实际结果、源码SHA/指纹、浏览器API来源、截图及包哈希统一记录于忽略的others/reports/b-ui-a-integration/；B套件在主线的原始输出为others/reports/b-ui/。构建成功、浏览器1440/390与原生运行分别记录；不将隐藏Windows DOM检查或模拟器结果称为实体手机/全部原生验收。最终以本轮实际报告为准。

## D 现在接续

原D先保存本树工作，再合并b-ui-integrated完整提交，执行[D-UI第二批目标](ai/D-learning-ui.md)。本批接B正式页面和样式，补学生班级邀请码加入、退出、审批等待/结果、撤销及本人历史状态等已有后端的界面。账号注册邀请与班级邀请码保持区别。学生只调用有权的本人/班级接口，历史记录不恢复当前班权限；缺少接口交A/B，不扩大读取管理接口或虚构成功。

D只改其登记范围，保持B七条注册、params和共享会话机制，不改B业务文件。助手、题库、考试、记录和监控继续真实未开放；使用frontend-design及已批准规范，不提前执行C/B2后的完整D目标。

## 验收边界

本次是B展示迁移的A集成，不代表全部既有UI或A2完成。D二次整合后，A/F仍须完整既有UI验收，再由A明确发布允许C开工的新基线。existing_ui_accepted_by_A与C_B2_new_features_allowed保持false。C开工前A仍须落实云端API与ASR worker的部署、鉴权、连接、超时和清理。

本轮不推送、不自动启动其他聊天、不更新云端；云端继续保留上次验收版本。语音、实体手机、正式安装器及C/B2后完整九组合按后续阶段分别验收。
