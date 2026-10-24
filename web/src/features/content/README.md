# D1 资料前端：组件里程碑

基线 e42dee58eefdeadf1fb5bbd462fefe47c8331703，ownership v6，D / codex/d-learning-ui-a2。2026-10-24实际设置为gpt-6.1-sol / medium / Default；不改全局设置。

## 当前真实范围

正式注册 `/content/materials`，学生/教师/管理员共用现有壳、会话和路由鉴权。当前公共契约仍0.3.2，没有资料生成SDK，正式页明确显示“资料接口尚未接通”，不发起候选API或返回模拟成功。B的七条路由和admin/teaching未修改。

`ContentWorkspace.tsx`提供受控展示组件：资料搜索/范围/分页、解析与发布分开状态、按对象动作、文件上传及字节进度、排队/解析/失败/结果不确定、定位文本预览、审核确认和固定版本发布确认。它们接收UI props与回调，不是HTTP客户端或平行SDK。数据请求、搜索竞态、取消代次、身份清理、幂等键、revision和真实下载由后续正式适配层消费A发布的生成客户端实现，不能用夹具通过代替这些验收。

## 设计与权限

沿用UI-2026.10-v1：青#087F8C、蓝#2563EB、工作底#F5F8FA、白#FFFFFF、正文#172B3A、辅助#607482；包内LabNoto。保留现有左侧导航和单一工作区，资料使用有标签的记录列表与局部动作，不增加虚构仪表盘或统计；390px一列，44px动作，长名换行。复用既有Dialog/Panel/SearchFilters，审核与上传沿用已有普通表单，不引入新的特殊交互。

库管理、提交、草稿编辑、审核、发布、预览、下载分别控制。`canUpload`不授予`canManageLibrary`，发布读取不授予草稿编辑。学生组件不展示管理写动作，若误传未发布记录则整批拒绝展示；这不代替服务端先授权再计数/分页/片段。React纯文本呈现提取内容，不执行HTML；定位为文本+页段，不扩Office渲染/OCR。

## 开发夹具与验证

Vite开发地址 `/src/features/content/dev/index.html`。入口永久标注“开发夹具 · 合成资料 · 非正式业务”，仅内存合成数据；模拟状态与动作回调不能称为真实业务成功。正式入口不导入夹具，生产Rollup入口不包含它。学生与教职夹具可切换，上传和解析状态可单独观察。

```powershell
. ./others/scripts/Use-ProjectEnvironment.ps1
pnpm run check
pnpm run build:web
$env:LABCONNECT_REPORT_STAGE='d1-content-components'
pnpm --filter @safelab/web exec playwright test --config tests/d-learning/content-components.config.ts
```

该配置只用于组件：保留公共Vite配置，在beforeAll核验D网页SHA/树/指纹/契约，不依赖尚未发布的资料API，不修改公共Playwright配置。检查数据是props夹具；所有/api/v1请求须为0，报告`component-source.json`明确`realMaterialApiValidated=false`。截图及结果保存在忽略目录others/reports/d1-content-components/。

## 等待真实技术基线

C02候选ecb7129497d1f6a69daf09df6db3f2f30537d7ba仅git show参考，未合入。本里程碑不代表D1或原C02完成。A发布资料迁移/真实路由/OpenAPI/生成SDK后，保存本树提交、普通合并完整SHA，再接通上传—解析—审核—发布—学生授权搜索—预览/原件下载并验证负向权限。

适配时重点核对候选仍缺的UI输入：VersionView没有资料可编辑revision/细分动作能力，也不直接表达当前绑定的publication/review状态；不得从身份、can_submit或解析成功推断这些权限/状态。应消费A正式发布的可验证查询/安全投影，或采用后端已授权且有revision的资源读取；公共字段需求交A，不手改SDK。审核绑定精确review revision/warning_hash和目标，上传按真实capabilities执行字节/hash约束，原件下载必须为二进制且再次鉴权。未接真实服务前不能开启产品写动作。

未实现资料编辑/库管理业务、来源元数据完整录入、chunk游标翻页、真实任务恢复/取消和传输下载适配；现有相关按钮仅验证props回调接缝。后续D2题库/学习、D3助手、D4监控尚未开工。
