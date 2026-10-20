# Shared backend

A1 实现 FastAPI/SQLModel/Alembic/PostgreSQL 的登录、当前授权、退出、课程列表/详情/创建。完整教学业务由后续模块扩展。来源和改动见 ../docs/upstream.md，真实 API 见 ../contracts/openapi.json。

A 维护总入口、接口契约和数据库迁移；B 维护 core/learning，C 维护内容/助手，E 维护监控。AI worker 使用 ../ai_worker 下独立环境，A1 不安装模型。

在仓库根目录运行以下 PowerShell 命令。先运行 `./others/scripts/Bootstrap.ps1` 准备本地环境；Docker Desktop 须已启动。

~~~powershell
docker compose --env-file .env -f others/deploy/compose.yml up -d --wait db
& ./others/backend/.venv/Scripts/python.exe -m alembic -c others/backend/alembic.ini upgrade head
Push-Location others/backend
& ./.venv/Scripts/python.exe -m app.seed
Pop-Location
./others/scripts/Start-Backend.ps1
~~~

默认服务 http://127.0.0.1:8000，文档 /docs；配置读取根目录被忽略的 .env，不依赖调用者 cwd。合成账号和随机密码保存在被忽略的 others/runtime/demo-accounts.json；生产环境禁止运行 seed。虚拟环境位于本目录 .venv，不向客户端交付。

权限测试：在本目录运行 `./.venv/Scripts/python.exe -m pytest -q`，使用独立本机 PostgreSQL 数据库 safelab_a1_test，每个用例回滚自己的测试行。它不使用 SQLite，不删除开发数据卷。

部署镜像从根目录运行 `docker build -f others/backend/Dockerfile -t safelab-api:0.1.0 .`；通过环境变量提供 DATABASE_URL、SECRET_KEY、APP_ENV=production、CORS_ORIGINS。迁移须先在同一版本镜像中执行。客户端发布包通过配置的服务地址访问，数据库凭据仅在服务端。
