# 安研通 UI-2026.10-v1 冻结设计包

版本UI-2026.10-v1。用户已明确批准网页v1，移动稿和规范现已补齐，供A接收、原D实施。桌面批准SHA为b67ad77cd49c2b5f99d2037e5828c29433ea66a6，原文见[approval.json](approval.json)。本包仍是设计资料，不是产品已迁移证明。

本目录是独立的设计资料和离线静态原型，不是产品实现。图片全部使用合成资料；设计静态页不连接业务API，不读取本机配置、密码或密钥，不导入产品入口。字体、图形、界面内容来源分别记录。

## 范围与基线

- 分支：codex/ui-design-v1；起点 b1-ready / 1e1011b4ff2e3c5a66b22492fb87a671e9699584。
- 只修改本目录。A已收到临时设计支线登记；原D仍负责产品代码实施。
- 保留已批准的蓝绿、实验室轻立体及全部已有界面；已补16组390px参考与完整视觉、状态、平台和迁移规范。
- 现有功能包括登录、服务设置、首次改密、学生课程、教师/管理课程班级、组织、账号授权、CSV、学生邀请及班级名单/审批/协作/交接/归档。
- 题库、考试、助手、监控、学生新工作台不在本轮设计范围，既有未开放项保持未开放。设计不暗示这些能力已完成。

## 评审方式

完成后通过 index.html 查看图片目录，PNG可单独打开；prototype.html是纯静态画布，选择屏幕只改变本地示意内容。render.cjs负责用共享Playwright和本机Edge导出1440px图片，并验证无外部或业务网络请求。

- [网页图片图册](index.html)：53个画面及2张长表单补图，批准来源和55张PNG哈希均未改变。
- [移动图册](mobile-gallery.html)：16组390px首屏、长页及4张滚动补图；长页为阅读方便将学生底栏放在页尾，首屏展示真实固定位置。
- [视觉与组件](design-spec.md)、[参数JSON](tokens.json)、[状态](state-spec.md)、[三端适配](platform-spec.md)。
- [53幅页面映射](functional-map.md)、[逐项功能迁移](migration-checklist.md)、[交接给A/D/B/C/F](handoff.md)。
- [网页历史检查](visual-review.md)、[移动最终检查](mobile-review.md)、[冻结文件清单](freeze-manifest.json)。
- [素材来源与许可](SOURCES.md)：原字体/OFL、4张原创器材SVG、图标，正式资源须迁入web，不依赖设计树。

可直接双击index.html看图。需要在浏览器查看静态画布时，在设计工作树根目录运行：

~~~powershell
node .\others\design\ui-redesign\render.cjs --serve
~~~

打开命令输出的临时本机地址，结束时按Ctrl+C。重新导出用同一命令去掉--serve；它只启动本目录的临时静态服务器，不启动后端或产品前端，也不占用A/B/C/D固定端口。

直接双击mobile-gallery.html可看移动图。移动复现与只读冻结检查：

~~~powershell
node .\others\design\ui-redesign\render-mobile.cjs
node .\others\design\ui-redesign\render-mobile.cjs --audit-all
node .\others\design\ui-redesign\extract-assets.cjs
node .\others\design\ui-redesign\render.cjs --gallery-only
node .\others\design\ui-redesign\freeze.cjs --check
~~~

qa-desktop.json保留批准前出图事实，approval.json记录之后的批准。qa-mobile.json记录16组参考，responsive-audit.json记录全部53个既有画布的390px静态布局/字段检查；不是业务或原生验收。小视口与24px安全区模拟不等于真实Android键盘/返回通过。重渲染受浏览器或时间影响时作为新记录，不能覆盖已批准图后仍声称哈希不变。

图片版本、页面角色和说明放在评审目录中，不把实现说明混入产品文案。设计批准需要用户明确指出版本；文件存在、图片生成或自动检查通过都不表示已经批准。

## 后续交接

移动与规范已齐，A接收最终完整SHA后登记桌面批准/冻结并发布D-UI基线；原D/B/F按所有权迁移。所有后续UI使用frontend-design和本版规范，常规新页自主设计/实现/截图自查，明显偏离风格、业务或权限再确认。既有UI真实回归和Windows/安卓运行通过A验收后再进入C→B2→D后续接入→A2；静态截图不能替代。

当前不修改项目入口、数据库、接口、SDK、共享依赖和全局模型配置，不推送Git。
