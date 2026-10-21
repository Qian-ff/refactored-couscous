# UI-2026.10-v1 冻结设计交接

接收方A；实施牵头为原D（codex/d-learning-ui-a2），业务展示层仍归B，原生适配归F，后续C沿用规范。此设计聊天只交付设计资料，不实施产品迁移。

## 批准与包内容

- 用户明确回复：“批准 v1，继续移动稿与规范”。[批准记录](approval.json)绑定桌面提交b67ad77cd49c2b5f99d2037e5828c29433ea66a6及UI-2026.10-v1。
- [网页图册](index.html)：53个画面＋2张长表单补图；批准的prototype.html/css/js与55张PNG均保留原哈希。
- [移动图册](mobile-gallery.html)：16组390px参考，含首屏、长页与必要的滚动补图；长页全图为便于阅读将学生底栏放在页尾，真实固定位置看首屏图。
- [视觉规范](design-spec.md)、[参数JSON](tokens.json)、[状态规范](state-spec.md)、[三端要求](platform-spec.md)、[53幅功能映射](functional-map.md)、[操作与角色迁移表](migration-checklist.md)。
- [素材来源](SOURCES.md)、assets/fonts中的原字体与OFL、assets/illustrations中的4张原创SVG和assets/icons.svg；可迁入web资源范围，不能让正式包依赖本目录。
- qa-desktop.json是批准前真实出图记录；approval.json是之后的用户批准，两者时间含义不同。qa-mobile.json记录移动图，responsive-audit.json记录全部53个既有画布的390px静态布局/字段检查；均不代表业务或原生测试。
- freeze-manifest.json列出最终交接文件SHA256，排除清单自身，避免自引用；最终Git SHA由本轮提交后向A报告，不写入自身造成循环提交。分支codex/ui-design-v1，起点b1-ready / 1e1011b4ff2e3c5a66b22492fb87a671e9699584。

## A接收

1. 读取用户批准证据、最终完整Git SHA、freeze-manifest.json及本轮差异，核对只含others/design/ui-redesign/前缀。不强制重置设计树或夹带主线改动，不自行推送。
2. 在主线登记桌面已批准与最终冻结SHA，接收设计资料，发布D-UI执行基线。A已用3ccb643提交持续frontend-design规则、临时树登记与阶段顺序；本轮应把原“等待网页批准”更新为已批准/设计已交接。
3. 保留七角色所有权，明确D/B具体文件交接与唯一修改者。D先建立公共组件，B再接自身展示层；不让两个聊天同时改ui.tsx/公共壳。
4. 原D的可执行Goal以主线others/docs/ai/D-learning-ui.md中的D-UI段为入口；将其中批准SHA和冻结规范绑定本包，再恢复D/B/F。C/B2新增功能继续等既有UI通过A验收，不能仅因图片批准就越过产品验收。

## 各角色迁移清单

| 接收方 | 工作与边界 |
| --- | --- |
| D | 必须使用frontend-design；采用tokens、包内资产与组件/状态规范，维护共享壳、导航、登录、服务连接、首次改密、学生现有课程页、正式路由和B页面注册。处理双main/双padding。web/tests/d-learning/内做真实1440/390、键盘/触屏及路由回归，不替换B请求/会话逻辑。 |
| B | 只在features/admin、features/teaching及自身测试范围迁移展示层，使用D组件，不另造身份或视觉系统。按migration-checklist逐项保留目录/班级、组织/账号/授权/邀请、名单/审批/协作/转交/归档、CSV全流程及幂等/修订行为。跨范围变更交A。 |
| C | 本次没有新增内容/助手页面可迁移；UI验收后按A放行的新基线继续。新增页面必须frontend-design并沿用本版规范，自主设计/截图自查；不按本稿虚构已经开放的题库、考试或助手。 |
| F | 复用共享前端，包内字体/图形，检查Windows缩放及Android安全区/软键盘/返回/文件操作。根据A集成结果重建并实测，记录产物/源码版本；不能用390px网页截图替代原生验证。 |
| A / G | A集成并更新一键启动/演示入口、真实接口验证和三端重建；G保持独立验收。必须区分设计、网页功能和三端运行证据。 |

目标档位A=max，B–F及设计=xhigh，G保持原安排。本设计聊天的新轮次已核验xhigh，证据摘要在registration.json。B/C/D最近历史轮次为max，恢复时分别核验新轮次；E/F启用时核验。任务书文字不等于档位已生效，不改全局默认。

## 给原D的执行起点

~~~text
/goal 作为安研通原D，按A发布的D-UI基线和UI-2026.10-v1冻结交接，完成全部已有界面的三端共享UI改版，交A专项验收。先读AGENTS、主线D任务、UI协作门禁、批准记录、freeze-manifest、design-spec、state-spec、platform-spec及migration-checklist，核对A指定完整SHA、登记树/分支、权限和当次xhigh。

每次UI工作使用frontend-design并沿用已批准的实验室轻立体风格；按既定规范自主实现和截图自查。D唯一负责公共设计系统、App/main/routes、现有登录/服务设置/首次改密/学生课程及正式B页面注册；B负责业务展示层，A先明确跨文件交接。三端共用一套前端与服务端规则，资产迁入web，不依赖设计目录。

逐项保留清单中的已有功能与真实状态，保留会话、查询竞态、范围判权、revision、CSV原子提交和同键重试；不把静态div控件或纯展示壳整段覆盖业务逻辑。未实现的题库、考试、助手、监控不提前开放。移动管理功能完整，44px命中区、全屏表单、安全区与返回按规范；原生部分交A/F验证。

运行类型、构建、真实接口和1440/390/键盘触屏回归，记录截图及API/前端来源。每轮只暂存本轮相关文件、本地commit并交A，不自行推送。A更新并实测一键演示、重建运行Windows/Android后完成既有UI专项验收，再放行C→B2→D后续接入→A2。图片批准不等于产品验收，缺失的真实行为和原生证据不能用静态图或mock替代。
~~~

## 本设计阶段的证据边界

设计阶段完成PNG、静态来源、图形/字体来源、功能与规范交接；没有运行正式后端、迁移数据库或修改产品代码。浏览器小视口与24px安全区模拟不等于真实Android键盘/系统返回验证；当前图稿不是Windows/Android运行或新功能可用的证据。
