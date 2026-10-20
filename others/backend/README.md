# Shared backend

A0在A1登录/课程切片上增加兼容CourseCatalog与当前工作身份，真实契约0.2.0；完整教学由后续模块扩展。运行状态见[a0-handoff](../docs/a0-handoff.md)，API见../contracts/openapi.json。版本唯一源../config/application.json；运行时/模型/公共迁移见契约，不另建重复目录。

A 维护总入口、接口契约和数据库迁移；B 维护 core/learning，C 维护内容/助手，E 维护监控。AI worker 使用 ../ai_worker 下独立环境，A1 不安装模型。

新 B/C/D 工作树先按 [共享环境](../docs/shared-environment.md) 使用主线解释器和配置，不重复 Bootstrap 或建 .venv。以下初始化与迁移仅由 A 在主工作区执行；Docker Desktop 须已启动。

~~~powershell
docker compose --env-file .env -f others/deploy/compose.yml up -d --wait db
& ./others/backend/.venv/Scripts/python.exe -m alembic -c others/backend/alembic.ini upgrade head
Push-Location others/backend
& ./.venv/Scripts/python.exe -m app.seed
Pop-Location
./others/scripts/Start-Backend.ps1
~~~

默认服务 http://127.0.0.1:8000，文档 /docs；配置读取根目录被忽略的 .env，不依赖调用者 cwd。本机学生、教师、管理员演示密码统一为 `88888888`，初始化工具将其写入 SAFELAB_DEMO_PASSWORD；完整合成账号保存在被忽略的 others/runtime/demo-accounts.json。生产环境禁止运行 seed。虚拟环境位于本目录 .venv，不向客户端交付。

修改已有演示账号密码时，先修改根 .env 的 SAFELAB_DEMO_PASSWORD，再在本目录运行 `./.venv/Scripts/python.exe -m app.seed --reset-passwords`。此命令只更新固定演示账号的密码哈希、使其旧登录会话失效并同步本机账号文件，不重新建立课程或权限。普通 seed 和一键启动不会重置已有密码。

`88888888` 仅为内置演示账号的约定。后续 B 实现正常创建/导入账号及改密功能，自建学生、教师、管理员账号各自设置密码；演示密码重置只匹配固定样例 ID，不按角色批量覆盖其他账号。

权限测试从根目录用python others/scripts/shared_env.py backend pytest -q --tb=short，共享串行锁，真实独立PG测试库。根conftest.py覆盖tests与app/domains。迁移测试只创建唯一前缀临时库并清理自己的库，不清空演示卷。勿绕过共享入口并行运行同一个测试库。

部署镜像从根目录运行 `docker build -f others/backend/Dockerfile -t safelab-api:0.1.0 .`；通过环境变量提供 DATABASE_URL、SECRET_KEY、APP_ENV=production、CORS_ORIGINS。迁移须先在同一版本镜像中执行。客户端发布包通过配置的服务地址访问，数据库凭据仅在服务端。
