# 已批准 UI v1：D-UI 执行交接

**v3当前接续**：当前环境前置已验收，资料前端由[D1](ai/d1-content-ui.md)接续、资料后端/worker由A副接续；其他新模块按[新版路线](delivery-workflow.md)。下文旧C/F及等待环境表述属于设计接收时记录，不作为当前开工门禁。

现行职责接收见[统一协作规范](coordination.md)：历史F由A副受托承接，E归C后续阶段；D仍唯一宿主/入口。以下批准、冻结与历史验证记录不改写，原放行限制同样约束新接收方。

产品实施更新：2026-10-23，[既有UI通过A集成验收](existing-ui-acceptance.md)，基线existing-ui-accepted；下文保留设计接收时的分工与要求。当前C/B2仍等A云端API/ASR前置及单独放行，不重复既有UI Goal。

2026-10-22，A接收UI-2026.10-v1冻结设计，发布本地执行基线ui-redesign-ready，完整SHA见A本轮交付及git rev-parse ui-redesign-ready。七角色所有权4、业务契约0.3.1和既有服务端规则保持不变；这是设计接收，不是产品UI已改版或三端已验收。

## 来源与验收边界

- 用户在设计聊天的明确回复为“批准 v1，继续移动稿与规范”；[批准记录](../design/ui-redesign/approval.json)绑定桌面b67ad77cd49c2b5f99d2037e5828c29433ea66a6。A已从该聊天人类答复独立核对。
- 最终冻结提交d17b342c53fc054bd298bee356143d3b3ab77af6；[清单](../design/ui-redesign/freeze-manifest.json)排除自身，A独立核对141个文件及Git内完整142文件集合，55张桌面PNG与批准时完全一致。
- 已补16组390px参考（16首屏、16全图、4滚动补图），并提供53画布的390px静态字段/动作、触控和溢出检查。图稿、静态检查和安全区模拟分别记录，不作为真实业务/Windows/Android验收。
- 规范入口：[视觉](../design/ui-redesign/design-spec.md)、[tokens](../design/ui-redesign/tokens.json)、[状态](../design/ui-redesign/state-spec.md)、[三端](../design/ui-redesign/platform-spec.md)、[功能迁移](../design/ui-redesign/migration-checklist.md)、[来源许可](../design/ui-redesign/SOURCES.md)。完整设计交接见[handoff](../design/ui-redesign/handoff.md)。

## 唯一修改者与文件分工

当前按原所有权执行，尚无跨角色文件转交。D牵头全部已有UI，不表示D可并行修改B的展示文件。

| 唯一责任方 | 文件与交接 |
| --- | --- |
| D | web/src/components/、styles/、routes/、features/student/、App.tsx、main.tsx及web/tests/d-learning/。在components/labconnect/导出公共组件，正式字体/图形放该目录assets/并保留来源，不从others/design导入运行资源。D整合PageRegistration和正式壳/导航；基础组件不反向导入B页面。 |
| B | web/src/features/admin/和teaching/及本范围测试；尤其teaching/ui.tsx、business.css和业务页面始终由B维护。D公共组件交接后，B把这些展示适配为公共组件，保留会话/请求/命令钩子与真实接口，处理双main/双padding。 |
| A | 后端总入口、公共API/类型/SDK、依赖与锁、公共测试配置/辅助、web/tests/foundation.spec.ts、根启动器及others/scripts。正式字体采用时由A补others/licenses/许可归档，供既有三端打包流程收录；本次设计接收不改这些产品文件。 |
| F | desktop/、android/、web/src/platform/；复用共享前端，配合真实缩放、安全区/软键盘/返回/文件适配及打包。待D/B实现被A集成后再做原生运行，不建立单独界面或提前扩展语音/监控/正式安装器。 |
| C / G | C继续等待既有UI验收放行，未来页面沿用本规范；G按原安排独立验收，不替代用户批准。 |

需要修改上述范围以外文件时，先交A登记具体文件、唯一修改者、交回条件和依赖提交，再实施。设计聊天保留只读设计交接身份，不接管产品实施。

## 接续顺序

B展示迁移6682ec37a2543e9e50a1bf400a8d70057351c807已交A接收，使用新基线b-ui-integrated；原D从[B-UI交接](b-ui-integration-handoff.md)继续二次整合。公共组件/壳/账号/学生课程及B教师管理展示已交付，D学生加退班/申请/撤销和A/F完整既有UI验收尚未完成。原d-ui-components-ready及冻结标签保留。

1. 原D保留本树提交后合并ui-redesign-ready或A公布的等价完整SHA，核对实际D分支、共享依赖、冻结文件及当次xhigh，执行[D任务书中的D-UI Goal](ai/D-learning-ui.md)。当前可以开始D公共组件和壳，完整D学习/考试Goal仍等待C/B2。
2. D先交付真实公共组件、布局和组件属性说明，在D所属目录记录导出/使用方式及检查并提交给A。A集成后发布新公共SHA；B保留提交后合并该SHA，再执行[B-UI Goal](ai/B-core.md)迁移教师/管理展示层。B在此前可核对功能映射和现有回归，不以假组件先完成迁移。
3. D负责正式路由和B页面注册，B负责所属页面；双方各自提交，A按实际依赖逐批集成。公共入口不导入开发夹具；设计画布的静态div控件、合成数据和connect-src none不能直接覆盖真实产品。
4. A更新并实测本阶段一键演示，A/F重新构建运行三端并记录源码/契约及真实证据。按功能映射保留首次改密/身份收窄、范围鉴权、CSV预检/原子提交/同键重试、查询竞态、名单/审批/协作/交接/归档；检验1440/390、键盘触屏及全部失败状态。
5. A明确验收通过并发布允许C开工的新完整SHA后，才进入C→B2联合验证→D后续接入→A2。当前product_migration仍未验收，C/B2新增功能未放行；本轮及D-UI专项不触发checkpoint-2推送。

## 可复核命令

悬浮助手v1.1规范另已接收，见[后续助手交接](assistant-floating-handoff.md)和本地ui-assistant-design-ready。该标签供保存本树工作后合并新规则，原UI-v1标签及上述已有页面迁移责任不变。当前D-UI继续保留助手未开放状态；后续由D唯一宿主承载C内容，不新建独立助手对话页。

```powershell
git rev-parse ui-redesign-ready
node .\others\design\ui-redesign\freeze.cjs --check
python .\others\scripts\check_preparation.py
python .\others\scripts\workflow.py status --baseline ui-redesign-ready
```

角色树需先合并最新执行基线再称就绪；A不会重置或替换其他树。后续常规新UI仍使用frontend-design与本冻结规范，自主设计/实现/截图自查，显著偏离风格或改变业务/权限再确认。
