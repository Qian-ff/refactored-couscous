# B1 集成交接：组织账号与课程班级

2026-10-21，A / main 接收B最终完整提交b6bf07f81aa64c17dc90e841d895fe260217aa90；B独立验收源码f10b7a140b22311e3075580001b1759058b5b7ba，最后一笔只补交接文档。真实契约继续为0.3.1，模型、OpenAPI形状和SDK未变，迁移头仍为b1c0e0a00001，不追加空迁移。

## 本阶段范围

组织、账号、邀请、首次改密与会话撤销、CSV预检/原子提交/幂等、目录/教学班、名单/审批/协作/交接/归档、范围内搜索、C资源授权服务及独立教师/管理业务组件已交付。B的逐项结果见[最终交接](../backend/app/domains/core/handoff/b1-completion.md)。正式产品导航、学生学习考试、资料题库与语音仍按C→B2→D→A2接续。

本次补充的权限修正：创建回执重放重新验证原对象当前权限；目录负责人指定他人主教师时，只可确认原始开班信息，不能读该班名单或私有数据。被明确指定的异学院负责人可在目录所属学院开班，开到目录外学院仍须校管理员协调。

## 一键内部验收

双击根目录Open-B1.cmd，复用共享配置、数据库及主树服务，打开已有B开发夹具，明确标为内部独立组件预览。用忽略的others/runtime/demo-accounts.json中合成账号登录，可查看组织账号、目录班级及班级管理。Open-B1-API.cmd仍提供真实API文档入口。原Open-Web/Windows/Android/A1继续使用现有产品入口。

Open-B1不是正式发布入口，开发夹具不进入生产网页或原生包。D后续统一接入PageRegistration与HashRouter；当前客户端重建验证共享账号课程切片兼容性，不据此声称B1管理页面已进入原生工作台。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\others\scripts\Start-B1.ps1 -NoOpen
$env:LABCONNECT_API_URL='http://127.0.0.1:8000'
pnpm --filter @safelab/web exec playwright test --config src/features/teaching/dev/playwright.config.ts
```

组件测试报告位于当前树忽略的others/reports/b1-components，测试只新增合成资料及班级，不重置演示库。首次改密、兼任身份收窄、真实CSV提交响应丢失后同键重试、名单/审批/协作/交接/归档、目录负责人不获委派班入口、同身份查询乱序均有真实操作断言。B源报告的15个文件哈希已核对，包含12张1440/390布局截图。

A合并后真实PostgreSQL/API全套68项通过（33.68秒），Ruff、TypeScript、实际OpenAPI/版本哈希/SDK一致检查、准备文件及链接检查通过。B独立验收为5项真实Edge场景全过；主树再按已提交源码运行组件检查和客户端兼容，结果分别记录，不能混用不同工作树的证据。

主树本轮API/客户端构建、版本哈希、入口和运行结果最终汇总在忽略的others/reports/b1-integration/release.json；每端产物源码以同目录builds.json为准，不能拿历史0.3.1包冒充本次集成包。Windows为未签名测试目录，安卓为debug APK，壳版本仍0.1.0。实体设备、原生录音、完整三端九组合在A2验收。

## C / D 接收

C保留自己的改动后合并A最终公布的完整SHA（本地b1-ready），核对当前树、契约0.3.1、所有权4和共享依赖，再使用[完整C任务](ai/C-content-ai.md)。本轮不自动启动或覆盖C工作树。

- [C授权服务与合成样例](../backend/app/domains/core/handoff/b1-content-access.md)：SQL先授权后计数/分页/检索；详情、下载和任务结果二次鉴权。复用学校/学院/目录/班级规则，不能共享兄弟班私有数据。
- [教师与管理页面注册](../../web/src/features/teaching/README.md)：adminPages / teachingPages，当前工作身份、courseId及登录/改密/个人资料交接。D唯一维护正式入口，禁止导入开发夹具。
- [A2模块协议](../contracts/a2-protocols.md)：B2考试门控仍明确unavailable。C先用教师验证问答/中文语音，学生状态不可核实时暂停；B2联合验证不构成C完成的循环前置。

B1完成不等于B2、D或A2完成。历史a2-ready、b1-api-0.3.0及b1-api-0.3.1均保留；本轮仅本地提交/新b1-ready，A2完整集成验收后才到已授权checkpoint-2推送节点。
