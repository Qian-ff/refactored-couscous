# 安研通 · 三端悬浮助手图片候选 v1.1

版本 **UI-ASSISTANT-2026.10-v1.1**，状态：**图片候选，等待用户明确批准**。

- [全部图册](index.html) / [三端总览](preview.png)
- [吸边修改前后对照](edge-comparison.png)：v1.1从露64px改为露48px，128px胶囊隐藏80px，恢复区48×56px。
- [网页面板细节](images/web-dialog-detail.png)
- [手机小窗](images/mobile-small.png) / [手机全屏](images/mobile-full.png) / [手机输入模拟](images/mobile-keyboard.png)
- [个人设置](images/mobile-settings.png) / [四款外壳](index.html#preferences)
- [设计计划与自查](design-plan.md) / [状态说明](state-notes.md) / [来源](SOURCES.md)
- [图片清单](inventory.json) / [静态检查](qa-report.json)

这里是隔离的静态设计资料。对话、课件引用、姓名、课程、时间均为合成示例；问答、录音、播放、权限按钮只演示本地状态。没有连接业务API，没有读取环境配置、账号文件或密钥，没有调用实际设备录音或扬声器。

本次修订依据用户“半隐藏可以更收进去一点”的反馈，尚未获得图片批准；前版候选保留在Git提交452d2658de805c22c4cbb0eb57b2aa70a3d4a298，专项目录名称沿用登记的assistant-floating-v1。

背景以已批准UI-v1课程画布为基础；仅在浏览器内把“学习助手”的未开放提示改成未来唤起入口示意，原背景文件不变。Windows标题栏/125%/150%及Android状态栏、安全区、软键盘均为浏览器布局参考，不是原生运行验收。手机全屏的空白是短对话后的正常对话流空间，不放无数据支撑的推荐或统计填充。

## 查看与复现

直接打开index.html可看PNG。静态原型建议通过本专项的隔离服务访问：

```powershell
node .\others\design\ui-redesign\assistant-floating-v1\render.cjs --serve
```

命令打印仅本地回环的临时网址；Ctrl+C关闭。静态服务只暴露设计目录，不启动产品服务。

重新出图使用项目已有Playwright和本机Edge，无新增依赖：

```powershell
node .\others\design\ui-redesign\assistant-floating-v1\render.cjs
node .\others\design\ui-redesign\freeze.cjs --check
```

可用 `--only=web-dialog,mobile-small` 做局部检查，结果写入忽略的qa-partial.json；最终交付以完整qa-report.json为准。受限环境不能启动Edge时，需要正常本机进程权限；没有通过改系统、浏览器策略或全局依赖解决。

## 批准门禁

本轮只交图片、静态来源及状态说明；没有最终冻结清单，没有图片批准记录，也没有产品实施授权。用户批准具体候选后，再补最终尺寸/边界、状态转换、tokens、无障碍、偏好保存、功能映射和A/C/D/F/B交接，由A接收并分发。既有UI的A验收与C/B2开工门禁继续有效。

设计聊天使用已登记树及codex/ui-design-v1；本专项仅新增本目录。原UI-v1的141清单文件保持原始字节。每轮本地提交，不自行推送。
