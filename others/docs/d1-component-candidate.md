# D1组件候选接收与资料接口接缝

2026-10-24，A收到D里程碑并实际read_thread核对轮次`01a16e31-114d-7c42-9dc4-aa36e67e19b7`已completed。候选`fbe0c568f2c7e665177744328e2798c1640aa136`，基线`e42dee58eefdeadf1fb5bbd462fefe47c8331703`。**当前只登记组件候选，不合入main，不登记D1或C02完成。**

## 已核对与证据边界

- Git范围9文件：content组件/说明/开发夹具、公共ApplicationShell及D浏览器测试，均属D所有权；未改后端、SDK、B页面或冻结设计。候选和范围说明可通过git show读取，不要求用户找临时文件。
- 已读取D树`others/reports/d1-content-components/delivery.json`：source_sha为该候选，契约0.3.2，7项组件浏览器检查无跳过/失败、类型/构建/冻结清单/生产隔离检查通过；`realMaterialApiValidated=false`、`D1Complete=false`。这是D测试证据，A本次未独立重跑UI/三端或逐张验收16张截图。
- 正式资料路由仅显示接口未接通，组件夹具不代表真实上传/解析/审核/发布/检索/下载。来源录入、库/草稿编辑、chunk游标、真实恢复/取消/下载适配仍待后续同包完成。

## A给A副的接入决定

本决定属于现有c02-public-integration公开查询/安全投影接入，不新增业务权限、不要求C回来修复；views、queries、management_queries、routes和公共HTTP测试已在具体生效委托内。执行基线仍e42dee58…，可用git show读取本补充，无需丢弃当前工作或为纯交接文档中断集成。

1. 给D提供可验证的**资料编辑revision**来源：复用获授权的资料详情或扩展最小安全投影，必须是MaterialChange实际消费的资料当前revision。不能拿VersionView.version_no、ReviewView.revision或PublicationView.revision代替；库修改、审核决定、出版/撤回各用其实际资源revision。后端继续做并发/授权校验。
2. 提供按当前身份、学校/学院范围、具体库/资料/版本及目标计算的**细分动作能力**，至少足够分别判断库管理、提交、草稿编辑、审核、发布、预览、原件下载。复用既有C-01/服务端权限与状态判定；S提交权不推出整库管理，已发布R不推出草稿读改，身份或解析成功不构成写权限。
3. 提供当前视图所针对的**review/publication绑定**来源：精确version_id、target_library_id、review_id/revision、warning_hash及当前出版绑定/active状态可通过获授权查询组合获得，不强制把内部模型全塞进VersionView。字段实际名称由公共DTO实现确定，交D真实OpenAPI/SDK及调用说明；学生安全DTO不返回无权审核/草稿管理细节。
4. 同一版本在目标A发布、在目标B仍待审核可以并存；状态/动作必须关联具体目标，不能给整个版本合成唯一“已发布”而误开放另一个目标，也不能让分页外/无权目标改变当前行状态。搜索先授权再计数/片段。服务端查询做有界批量读取，不要求前端扫描所有审核/出版记录来拼状态。
5. 页面能力是显示/动作接缝，**所有写操作与下载仍重新判权**。撤权、旧revision、过期审核/warning_hash和旧publication绑定按真实401/403/409等契约拒绝，不能凭先前capability绕过。
6. 补真实API/受限角色检查：S与整库管理分离、发布读取与草稿编辑分离、同版本多目标不同状态、身份/范围撤销后GET与POST竞态、错资源revision和旧review绑定、学生投影隔离。用实际路由导出SDK后再交D，不手写平行客户端或把提案字段当已发布。

## 交给D的下一步

D保留fbe0c56，等待A明确发布技术SHA后再合并并完成正式适配。当前组件的单一publication枚举只是当前行展示，正式适配须按目标绑定，不从解析成功/can_submit/教职身份推导状态或权限；如真实契约需要多目标选择，在D范围调整，普通接缝无需重开全部设计。

下一责任：A副在现有包中完成真实安全查询投影和运行接入→A审核迁移/HTTP/权限/SDK证据并发布技术基线→D接真实资料闭环→A副复验合并版本→A才判定C02整包完成。C1首次新模块另按用户手动首启，不成为资料收尾前置。
