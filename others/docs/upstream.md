# A1 来源与适配

固定来源：FastAPI full-stack-fastapi-template 0.12.0，提交 `84c5a9e11a9e58262599e3d772f5386924e02ca7`。
官方源码：https://github.com/fastapi/full-stack-fastapi-template/tree/84c5a9e11a9e58262599e3d772f5386924e02ca7
下载 ZIP 的 SHA256：`777c6118156f87ffa07a9946b201a5df71a186ec2c6b2de01bc016f2fe0ce3d7`。
MIT 原文保存在 others/licenses/fastapi-template-MIT.txt。

保留并适配 Settings、Argon2/bcrypt 密码工具、JWT、SQLModel Session、FastAPI operation ID、Alembic 环境、shadcn Button/utilities 和 hey-api 生成器配置。身份、组织与课程模型按本项目设计实现，替换上游 User/Item 演示。后端是独立 uv 项目，重新生成自己的锁文件，未冒用上游根工作区锁。

上游前端重构为 A1 最小中文课程工作台，沿用 React/TypeScript/Vite/Tailwind/shadcn 技术。上游前端所有 Bun 入口由 pnpm scripts 和 Node/Python 脚本替代；后端容器不再内嵌 Bun 前端构建。原邮件、Traefik、FastAPI Cloud 自动部署和上游演示测试不接入本项目，避免附带云部署动作。

Python 直接依赖固定为上游 uv.lock 中版本；删去 A1 不用的邮件、Sentry 等依赖。前端与原生工程版本、完整传递依赖由本项目锁文件记录。AI worker 另建环境，A1 不安装模型。
