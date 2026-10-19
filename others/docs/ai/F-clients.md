# F：Windows 与安卓任务书

请作为 SafeLabPlatform 的 F 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，用户当前仅完成准备工作，应用尚未实现。

## 开始前

1. 打开自己的独立工作区 others/worktrees/clients，确认当前分支为 task/clients。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 等待 A 发布可运行骨架、迁移和真实 OpenAPI 的基线；在干净的本分支 merge main 后再开始相互依赖实现。

## 本角色任务

1. 基于共享网页产物建立 Electron 与 Capacitor 工程。
2. 实现可配置服务地址、安全凭据、文件选择、麦克风/摄像头及返回键适配。
3. 建立 Windows 安装包与 Android APK 的真实构建命令。
4. 实机检查登录、三角色、录音、上传和网络；干净目录运行时不依赖开发路径。

## 修改范围

- desktop/
- android/
- web/src/platform/

范围以 ownership.json 为准。依赖、公共路由、数据库迁移及共享类型的变更交给 A，提出需求和兼容影响即可，不在其他聊天文件中临时绕过。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/clients；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
