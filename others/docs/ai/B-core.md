# B：账号与业务管理任务书

请作为 SafeLabPlatform 的 B 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/core，确认当前分支为 task/core。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 实现学校、学院、专业、账号、角色授权、导入/邀请与重置密码。
2. 实现课程主教师/协作、跨学院选课、入退课审批、名单调整、教师交接和归档。
3. 实现培训记录和自动达标规则；服务端判分与学习领域接口按契约协作。
4. 实现对应教师课程管理和管理员业务页面；验证权限撤销与历史保留。

## 修改范围

- others/backend/app/domains/core/
- web/src/features/admin/
- web/src/features/teaching/

范围以 ownership.json 为准。依赖、公共路由、数据库迁移及共享类型的变更交给 A，提出需求和兼容影响即可，不在其他聊天文件中临时绕过。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/core；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
