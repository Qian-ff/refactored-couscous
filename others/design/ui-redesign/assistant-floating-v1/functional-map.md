# 批准设计到产品实施的功能映射

UI-ASSISTANT-2026.10-v1.1，48张主画布绑定批准提交7a678db。现有助手只有未开放占位，以下功能仍需责任角色实现；本清单不能当作完成声明。桌面/手机使用同一业务和单例，覆盖学生、教师、管理员各自授权范围。

| 功能 | 新版位置与保留行为 | 责任 |
| --- | --- | --- |
| 唤起/导航 | 胶囊文字/语音、原助手导航唤起同一宿主；未登录隐藏、设置关闭引导设置 | D/C/A |
| 大小/拖动/吸边 | 桌面420×560；手机70%×43%、全屏输入；左右露48×56，点击恢复；不误录音 | D/F |
| 个人设置 | 当前账号菜单进入；显示/四款外壳/语音自动播报按本设备账号范围记住 | D，F适配本地存储 |
| 上下文 | 新对话继承当前授权班，无班先选；旧会话固定范围并显示，切页面不混资料 | C/A，D提供路由上下文 |
| 对话/续问 | 面板正文与固定输入；当前有效会话草稿/请求代次；停止生成及收起完成点 | C/D/A |
| 历史/删除 | 助手内部最近对话、新建、当前单删、清空确认；服务端个人历史三端同步 | C/A，D布局 |
| 检索/引用 | 当前有权发布资料，固定版本/页段，资料不足明确说明，点击重新判权 | C/A/F |
| 录音 | 显式开始、停止/取消、可编辑识别文字、确认后问答；原音频默认删除 | C/F，A桥接协议 |
| 播报 | 文字手动、语音可自动；收起/吸边/关闭/后台/考试/身份变化停止 | C/F/D |
| 会话与权限 | confirmSession和现有代次/取消；学校、当前身份及课程授权由服务端检验，退出清旧内容 | A/C/D/B |
| 考试暂停 | 当前账号任一有效正式考试暂停新问答、旧会话、历史、引用、任务全过程；未知状态暂停 | B2/C/A，D显示 |
| 错误/空/未配置 | 真实原因、下一步和保留草稿；无假成功、静默换模型或未授权回退 | C/D/F/A |
| 构建/发布 | 三端共用前端；正式素材迁入产品，更新并实测一键入口和客户端 | A/F/D |

## 全部画布映射

图册链接对应批准画布，不能替代真实接口/原生验证。配色四张同时展示胶囊和面板；Windows四张为布局/缩放模拟；keyboard为视口模拟。

| ID | 图册画面 | 平台 | 主要交接 |
| --- | --- | --- | --- |
| web-capsule | [胶囊入口](index.html#web-capsule) | 网页 | D宿主/C内容 |
| web-dialog | [展开对话](index.html#web-dialog) | 网页 | D宿主/C内容 |
| web-history | [最近对话](index.html#web-history) | 网页 | D宿主/C内容 |
| web-dock-left | [左侧半隐藏](index.html#web-dock-left) | 网页 | D宿主/C内容 |
| web-dock-right | [右侧半隐藏](index.html#web-dock-right) | 网页 | D宿主/C内容 |
| web-settings | [个人助手设置](index.html#web-settings) | 网页 | D宿主/C内容 |
| web-disabled | [关闭后的设置入口](index.html#web-disabled) | 网页 | D宿主/C内容 |
| web-recording | [录音与停止](index.html#web-recording) | 网页 | D宿主/C内容 |
| web-transcript | [确认识别文字](index.html#web-transcript) | 网页 | D宿主/C内容 |
| web-generating | [文字生成中](index.html#web-generating) | 网页 | D宿主/C内容 |
| web-complete | [收起后的完成提示](index.html#web-complete) | 网页 | D宿主/C内容 |
| web-exam | [正式考试暂停](index.html#web-exam) | 网页 | D宿主/C内容 |
| web-unknown | [考试状态待核实](index.html#web-unknown) | 网页 | D宿主/C内容 |
| web-unconfigured | [学校尚未配置](index.html#web-unconfigured) | 网页 | D宿主/C内容 |
| web-offline | [服务连接失败](index.html#web-offline) | 网页 | D宿主/C内容 |
| web-mic-denied | [麦克风权限未开启](index.html#web-mic-denied) | 网页 | D宿主/C内容 |
| web-context | [选择授权教学班](index.html#web-context) | 网页 | D宿主/C内容 |
| web-new | [新对话继承当前班](index.html#web-new) | 网页 | D宿主/C内容 |
| web-delete | [删除对话确认](index.html#web-delete) | 网页 | D宿主/C内容 |
| web-clear | [清空全部历史确认](index.html#web-clear) | 网页 | D宿主/C内容 |
| windows-dialog | [Windows应用内悬浮](index.html#windows-dialog) | Windows | D/F |
| windows-compact | [Windows小窗口](index.html#windows-compact) | Windows | D/F |
| windows-scale-125 | [Windows缩放125%参考](index.html#windows-scale-125) | Windows | D/F |
| windows-scale-150 | [Windows缩放150%参考](index.html#windows-scale-150) | Windows | D/F |
| mobile-capsule | [手机胶囊](index.html#mobile-capsule) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-small | [可移动小窗](index.html#mobile-small) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-full | [完整对话](index.html#mobile-full) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-history | [手机最近对话](index.html#mobile-history) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-clear | [手机清空历史确认](index.html#mobile-clear) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-new | [手机新对话](index.html#mobile-new) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-keyboard | [输入与键盘避让](index.html#mobile-keyboard) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-dock-left | [手机左侧半隐藏](index.html#mobile-dock-left) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-dock-right | [手机右侧半隐藏](index.html#mobile-dock-right) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-settings | [手机助手设置](index.html#mobile-settings) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-disabled | [手机关闭后可恢复](index.html#mobile-disabled) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-recording | [手机录音](index.html#mobile-recording) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-transcript | [手机识别文字确认](index.html#mobile-transcript) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-exam | [手机考试暂停](index.html#mobile-exam) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-unconfigured | [手机尚未配置](index.html#mobile-unconfigured) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-offline | [手机连接失败](index.html#mobile-offline) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-mic-denied | [手机麦克风权限](index.html#mobile-mic-denied) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-360-small | [360px小窗](index.html#mobile-360-small) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-360-full | [360px全屏](index.html#mobile-360-full) | Android | D公共外壳/C内容，F手机桥接 |
| mobile-360-keyboard | [360px输入避让](index.html#mobile-360-keyboard) | Android | D公共外壳/C内容，F手机桥接 |
| theme-white | [经典白外壳对照](index.html#theme-white) | 配色 | D公共外壳 |
| theme-teal | [青绿外壳对照](index.html#theme-teal) | 配色 | D公共外壳 |
| theme-blue | [蓝色外壳对照](index.html#theme-blue) | 配色 | D公共外壳 |
| theme-charcoal | [炭灰外壳对照](index.html#theme-charcoal) | 配色 | D公共外壳 |
