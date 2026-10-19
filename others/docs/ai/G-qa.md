# G：独立验收任务书

请作为 SafeLabPlatform 的 G 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/qa，确认当前分支为 task/qa。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 从权限隔离、学习达标和监控闭环建立可复跑 API/E2E/故障测试。
2. 覆盖跨学院课程、变更教师、退课历史、重复提交、接口失败和密钥边界。
3. 检查三端安装、手机排版、录音、摄像头和包内敏感配置。
4. 独立汇总复现步骤、版本和证据；由责任聊天修复实现，自己复测。

## 修改范围

- others/qa/

范围以 ownership.json 为准。发现实现缺陷交责任角色修复，自己复测；接口、迁移与基线问题交 A，前端公共路由问题交 D。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/qa；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
