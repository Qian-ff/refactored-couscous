# API 约定

## 实际 0.3.0（兼容A0的0.2.0）

唯一版本源为 ../config/application.json。OpenAPI 只导出实际接口；version.json 记录真实导出哈希，web/src/client 由工具生成，不手改。/courses 继续表示教学班，响应新增 catalog_id；旧创建请求兼容。

B1真实组织/账号/目录/班级/CSV操作见[b1-public-handoff](../docs/b1-public-handoff.md)。新写入要求幂等键，修改带revision；输入校验错误不包含input/context。health增加migration并核验实际库头版本，未迁移返回503。B2等未来接口继续只保留设计，不生成占位SDK。

Bearer 凭据只存前端内存。X-Work-Role 取 student/teacher/administrator，由服务端在当前有效授权内确认。未显式选择按会话固定默认；教师兼管理员默认教师，撤权不回退管理员。非法或撤销身份403，停用/会话失效401；普通权限不足403。/auth/me 返回 grants（全部授权）、available_work_roles、active_work_role、effective_grants（当前身份）；业务判权只读 effective_grants。注销仍可在旧身份被撤销后撤销会话。

前端使用 web/src/lib/api.ts 的 configureService、setToken、confirmSession、switchWorkRole、logoutSession、subscribeSession。D 在 switching/closing/anonymous 或代次变更时清理页面、查询与敏感状态；成功确认后挂新页面。共享层取消旧请求，拒绝旧代次响应，过期401不会撤销新会话。搜索同身份下的新旧查询仍由所属组件取消或序号校验。页面没有第二套 token 或密钥参数。

允许的开发前端为 A/B/C/D 的5173/5174/5175/5176，包含 localhost/127.0.0.1；现有原生来源保留。CORS 允许 GET/HEAD/POST/PUT/PATCH/DELETE 和 Authorization、Content-Type、X-Work-Role、Idempotency-Key、If-Match。额外端口由 A 明确配置并验预检；不开放任意来源。

开发 /api/v1/dev/identity 与网页 /__labconnect/identity 提供启动时源码 SHA、工作树哈希、源码内容指纹、契约版本。启动器和浏览器验证全部匹配才复用服务。API 标识端点在 production 不挂载，也不进入 OpenAPI；正式 build-info.json 仅 SHA、内容指纹和契约，不包含本机路径/树标识。

## 未来接口规范（尚未实现）

- 服务端先以当前身份和学校/学院/资源关系授权；客户端 school_id、catalog_id、course_id 不构成授权。
- 查询参数有长度、分页上限和排序白名单；参数化 PostgreSQL 查询先授权再过滤、计数、稳定分页、片段与建议。文件/预览/下载/任务结果二次鉴权。基础搜索不依赖 AI。
- 写操作采用 Idempotency-Key；相同主体/工作身份/操作/键重复返回同一结果，载荷不同409。发布/编辑使用 If-Match 或明确 revision，冲突409，提交事务内再次鉴权。具体字段随真实接口导出。
- 长任务 queued/running/succeeded/failed/canceled，job_id、稳定错误码、进度和取消语义；创建、执行、结果均核验授权/配置快照，重型任务初期串行。
- 明确未配置、无权限、额度不足、连接/超时/模型结构错误、worker不可用；不得静默换服务商/模型、伪造成功或泄露供应商响应中的秘密。
- 正式作答和规则版本在服务端；保存返回 answer_revision/saved_at/deadline，使用服务端时间。答案学生 DTO 与教师 DTO 分离，公布策略由服务端执行。
- 密钥只在服务端 AES-GCM 保存，前端仅掩码/存在状态；测试→启用→新任务生效，失败保留旧启用版，学校只影响本校。
- 来源引用使用 material_id/version_id/page/paragraph，下载使用有权版本标识，禁止把任意本机路径或未授权 URL 当成资源授权。

具体跨阶段协议见 [a2-protocols.md](a2-protocols.md)。只有实现、迁移和检查到齐后才由 A 发布下一份真实 OpenAPI。
