# D：学习体验与设计系统任务书

请作为 SafeLabPlatform 的 D 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/learning-ui，确认当前分支为 task/learning-ui。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 实现蓝绿设计系统、角色导航、公共状态和桌面/手机响应式布局。
2. 实现学生首页、课程、6 个示范关卡结构、场景热点、剧情决策、徽章和复训。
3. 实现考试交互、分项结果、培训记录展示；正式判分调用服务端。
4. 为 C/E/F 提供组件和平台接口契约；原生代码由 F 实现。

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
