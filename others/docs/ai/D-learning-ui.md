# D：学习体验与设计系统任务书

请作为 SafeLabPlatform 的 D 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，A1 的实际实现、验收状态与可交接基线见 others/docs/a1-handoff.md；后续模块按已发布基线继续开发。

## 开始前

1. 打开自己的独立工作区 others/worktrees/learning-ui，确认当前分支为 task/learning-ui。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 当前基线为 checkpoint-1，包含最新一键工具及三角色/搜索要求；从交接报告核对后，在干净的本分支合并并确认 contains_baseline=true 再开始实现。

## 本角色任务

1. 实现蓝绿设计系统、角色导航、公共状态和桌面/手机响应式布局。
2. 实现学生首页、课程、6 个示范关卡结构、场景热点、剧情决策、徽章和复训。
3. 实现考试交互、分项结果、培训记录展示；正式判分调用服务端。
4. 为 C/E/F 提供组件和平台接口契约；原生代码由 F 实现。
5. 首个交付点 D1 为学生、教师、管理员分别建立首页、导航及工作区，支持兼任角色切换和桌面/移动布局；B 提供教师/管理员业务页，D 负责公共壳和路由注册。验收覆盖三平台乘三角色九种组合，不能只替换当前通用课程页的身份名称。
6. 为三角色提供课件搜索入口与共享查询/筛选组件，接入 C 的真实课件接口，协调 B/C/E 的列表搜索。处理中文输入、清空、分页、加载、无结果、错误重试及无权限；切换身份清除旧结果，旧请求不得覆盖新结果。需求和权限范围以设计第11节为准。

## 修改范围

- web/src/components/
- web/src/styles/
- web/src/routes/
- web/src/features/student/
- web/src/App.tsx
- web/src/main.tsx

范围以 ownership.json 为准。D 唯一维护前端入口与公共路由，协调各功能页面注册。依赖、后端路由、数据库迁移及共享类型变更交给 A；判分、进度和培训记录由 B 的服务端接口提供。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/learning-ui；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
