# B：账号与业务管理任务书

请作为 SafeLabPlatform 的 B 角色工作。本任务以根 AGENTS.md、设计基线与真实接口契约为准，A1 的实际实现、验收状态与可交接基线见 others/docs/a1-handoff.md；后续模块按已发布基线继续开发。

## 开始前

1. 打开自己的独立工作区 others/worktrees/core，确认当前分支为 task/core。
2. 读根 AGENTS.md、others/docs/design.md、others/contracts/README.md 和 ownership.json。
3. 当前基线为 checkpoint-1，包含最新一键工具及三角色/搜索要求；从交接报告核对后，在干净的本分支合并并确认 contains_baseline=true 再开始实现。

## 本角色任务

1. 实现学校、学院、专业、账号、角色授权、导入/邀请与重置密码。
2. 实现课程主教师/协作、跨学院选课、入退课审批、名单调整、教师交接和归档。
3. 独立负责学习考试后端：任务/考试、作答、服务端判分、学习进度、培训记录及自动达标规则；覆盖幂等、固定题目/规则版本和权限测试。C 提供审核后的固定题目版本，D 调用接口。
4. 实现对应教师课程管理和管理员业务页面；验证权限撤销与历史保留。
5. 按设计第11节实现有权限的课程、班级、学生/教师名单及培训记录搜索/筛选；协同 C 确定课件检索的选课/授课和管理范围。三角色数据权限先于检索计数、分页与返回结果。

## 修改范围

- others/backend/app/domains/core/
- others/backend/app/domains/learning/
- web/src/features/admin/
- web/src/features/teaching/

范围以 ownership.json 为准。前端公共路由交 D 注册；依赖、后端总路由、数据库迁移及共享类型变更交 A 集成，提出需求和兼容影响。

## 每轮交付

按根 AGENTS.md 检查并提交本轮文件到 task/core；回报 commit ID、可复现的验证命令/结果及未完成事项。无改动不建空提交。准备文件存在不代表功能已实现；以运行证据和 others/qa/acceptance.md 判断完成。客户端包不包含密钥、真实数据或源码路径依赖。
