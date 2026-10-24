# C1实施进度

完整范围、A已采用的接缝与用户确认见c1-plan.md，不恢复旧C02。

## 开工及基线

- 实际Default / gpt-6.1-sol / medium已由当前turn_context核验。
- 开工HEAD ecb7129497d1f6a69daf09df6db3f2f30537d7ba，清洁；计划保存提交8d74fe1。
- 按用户指定普通合并3cdb38310e2c4fbd8a514384b6670062752ef1eb，合并提交c4988616e5e1c58a5973b8450a9a6386878aa7a1，保留历史，无推送。
- Git登记、包含指定基线及ownership v6核验；shared_env inputs相符，业务解释器3.14.6解析本树app源码。受限进程读主树元数据失败后，以正常授权进程只读复核成功，未改系统设置。

## 领域基础候选

新增Question/Draft/Version、来源及审核发布绑定、ImportBatch/TransferTask/导出版本与导入结果关系；Lesson/Draft/Version、题目/来源绑定、SceneAsset及审核发布关系，共21张候选表。所有库、用户、会话、材料、题目/关卡/资产引用使用真实FK。来源chunk与version、JSON活动与关系表、不可变状态还须领域服务及A接入数据库保护，不把DDL编译当作保护已生效。

题目载荷四题型、答案/选项、来源、知识点、字节预算等严格校验；私有评分与StudentLesson/TeacherLessonPreview分开。纯学生投影不默认带来源，只接收另行鉴权的来源投影，呈现顺序独立于私有答案。此纯函数不是身份/课程/任务授权入口，完整受控服务待后续实现。

SVG采用有界被动子集：拒绝DTD、实体、外部资源、脚本、事件、foreignObject、style、处理指令和非SVG命名空间；限制深度/节点/属性/文本/字节，校验viewBox与数值。安全结果有规范化哈希，尚未生成六份正式示范SVG或注册公共资源接口。

## 检查

本轮23项纯测试通过（题目输入9、模型DDL3、关卡投影6、SVG安全5）。首次检查发现stdlib expat导入位置错误和测试中错误的模型计数假设，修复后全过。Ruff与git diff --check通过。

运行日志和源指纹留questions/test-results/c1/忽略区。未连接PG、运行迁移、安装依赖、生成公共OpenAPI/SDK或启动API；无业务API来源或真实沙箱通过结论。

## 下一步，完整目标保持

实现领域授权查询/服务/审核发布/共享复制/B2受控服务和候选路由；补CSV/XLSX纯CLI/任务协议、上传预检确认导出与清理接缝；约60题/六关待审核内容、许可及PG候选场景；完整M1交A副2接公共运行环境，再联合真实PG/HTTP/SDK/隔离验证。M1尚未达到，C1未完成，不向A重复发送普通局部进度，不自动启动后包。
