# 悬浮助手 v1.1：A 已接收的实施交接

现行职责接收见[统一协作规范](coordination.md)：历史F由A副受托承接，E归C后续阶段；D仍唯一宿主/入口。以下批准、冻结与历史验证记录不改写，原放行限制同样约束新接收方。

2026-10-23当前接续：既有UI及[云端API/ASR前置](cloud-asr-handoff.md)已验收，c-start-ready允许C执行内容/历史/语音业务与适配；B2、D正式宿主及F原生扩展按后续分阶段交接。下面保留设计接收时的事实，设计标签本身不授予额外权限；真实公共契约现为0.3.2。

2026-10-22，A从设计聊天独立核对人类回复“批准 v1.1，继续规范与 A 交接”，问题 call_540ea4383fa7468f9f9e039e50fec5ca、答复轮次 01a15fb5-60ae-7451-a5d5-8df427c809fd。批准图片提交 `7a678db1d3eee3055e0b369bb18952abf1d79676`，冻结提交 `78cdeb677ed1f302f1a3ecb68bfbd834aa4b85d1`。接收基线为本地 `ui-assistant-design-ready`，完整 SHA 用 git rev-parse 获取；旧标签保持原位置。

本次只接收设计和实施语义。真实契约仍为 0.3.1，没有新增 HTTP、迁移、SDK、助手产品代码或原生能力；当前只有未开放占位，没有可删除的已实现独立聊天页。

## 冻结规范与边界

- [批准记录](../design/ui-redesign/assistant-floating-v1/approval.json)、[图册](../design/ui-redesign/assistant-floating-v1/index.html)、[清单](../design/ui-redesign/assistant-floating-v1/freeze-manifest.json)。
- [视觉与尺寸](../design/ui-redesign/assistant-floating-v1/design-spec.md)、[状态/历史/偏好](../design/ui-redesign/assistant-floating-v1/state-spec.md)、[三端](../design/ui-redesign/assistant-floating-v1/platform-spec.md)、[功能映射](../design/ui-redesign/assistant-floating-v1/functional-map.md)、[后续验收](../design/ui-redesign/assistant-floating-v1/acceptance.md)。
- A核对94个清单文件及清单自身共95份Git文件、48张主图/59份PNG、27个SVG图标、20项静态交互记录及355个本地链接；批准PNG及截图源文件保持原字节，原UI-v1的141文件/55桌面图完整。静态交互报告与图片不替代真实三端验收。

三端统一使用应用内单例：胶囊128×56；网页/Windows通常420×560；手机小窗按可用宽70%和高43%重排，输入时展开同一实例。主动拖动吸边后隐藏80px、露48×56恢复区，恢复区只恢复窗口。四款纯色只改变外壳，正文保持浅色；个人开关、主题、自动播报和位置按当前设备/服务/学校/账号隔离。

## 唯一职责与后续目标

| 角色 | 交付边界 |
| --- | --- |
| A | 冻结共享宿主/生命周期/上下文/考试协议；实际领域实现到达后接公共类型、迁移、挂载和生成SDK；维护依赖、许可、基线及最终一键入口与验收 |
| D | 在既有 components/styles/routes 所有权内维护唯一 AssistantHost/Frame、胶囊/面板/全屏/吸边、拖动与键盘等效操作、个人设置、导航动作及宿主测试；唯一修改 App/main/routes |
| C | 在 features/assistant、后端 assistant 和 worker 自有范围实现个人文字历史、固定授权范围/引用、问答、录音识别确认和播报内容；导出宿主内容与生命周期回调，不注册独立聊天 PageRegistration，不再创建 fixed 容器 |
| B2 | 提供真实账号级 tutoring gate；与C验证新问答、历史、引用、旧会话及任务开始/执行/返回均受限，跨班/设备一致，未知状态暂停学生辅导 |
| F | 通过平台桥接适配真实麦克风/TTS、软键盘、安全区、返回、后台、缩放及打包；不新增系统悬浮权限或独立视觉实现 |
| E / G | E无新增监控任务，沿用现有规则；G按原安排独立验收，本次不唤醒 |

正式素材由D迁入其产品资源范围并保留来源，A补许可归档，F核对打包；产品不依赖设计目录。跨所有权文件仍先由A登记唯一修改者，不以本交接扩大任一角色的代码范围。

## 执行次序

继续 D-UI 公共组件 → A发布组件基线 → B既有展示迁移 → D整合 → A/F真实既有UI验收。验收通过后A另行发布允许C开工的完整SHA，才进入C → B2联合验证 → D后续助手/学习接入 → A2；本设计标签只提供已接收规范，不放行C/B2，也不要求D当前提前实现助手。

后续C先交公共适配提案，A统一正式名称/类型后D消费；不能让C/D各造一套宿主协议。其他内容管理和编辑器页面仍沿用PageRegistration，取消的只是独立助手对话页计划。期间已部署云端及三端基础验证单独见[云端交接](cloud-handoff.md)，不充当助手验收。

用户另在设计请求中明确计划阶段max、B–F及设计执行xhigh；A执行保持max，G原安排。此处登记目标，实际轮次逐聊天核验，不改全局配置或声称其他聊天已切档。没有自动启动业务聊天或推送，本地提交与标签供各树保存自身工作后合并。

## A接收复核

```powershell
node .\others\design\ui-redesign\assistant-floating-v1\freeze.cjs --check
node .\others\design\ui-redesign\freeze.cjs --check
python .\others\scripts\check_preparation.py
git rev-parse ui-assistant-design-ready
```

接收证据保存在忽略的 others/reports/ui-coordination/assistant-reception.json。冻结包自身保留设计交付时状态，不为填写A接收结果重写其清单或批准图。
