# Shared backend

计划：FastAPI、SQLModel、Alembic、PostgreSQL；业务接口和正式判分集中在本服务。应用代码尚未接入。

A 维护总入口、接口契约和数据库迁移；B、C、E 分别维护核心业务、内容/助手、监控领域。先由 A 输出可运行基础和 OpenAPI 基线，再展开依赖它的实现。

虚拟环境放本目录 .venv；连接配置使用本地忽略文件，不向客户端交付。迁移只按 PostgreSQL 同引擎设计。
