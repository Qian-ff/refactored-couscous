# 开源与素材要求

用户允许按适用开源条款交付组件。A1 已导入固定 FastAPI 模板的基础代码及 Electron/Capacitor 依赖；来源与适配见 upstream.md。未引入推理库或模型权重。

others/licenses 保存模板 MIT 原文、实际前端运行依赖的许可文本与版本来源清单；运行 `node others/scripts/licenses.mjs` 从已安装依赖更新。文本随网页 dist/licenses、Windows 资源及安卓网页资源交付。Python 完整依赖由 uv.lock 固定，安装后的发行包保留其自带 dist-info 许可。Electron 包另保留 Chromium 自带许可。

框架接入时逐项记录：名称、固定版本/提交、原始 URL、代码许可、权重许可、素材许可、修改及分发要求。代码许可不能替代模型或素材许可。完整许可证与 NOTICE 随适用组件交付。

选型来源：
- https://github.com/fastapi/full-stack-fastapi-template
- https://github.com/electron/electron
- https://github.com/ionic-team/capacitor
- https://github.com/SYSTRAN/faster-whisper
- https://huggingface.co/rabahdev/fire-smoke-yolov8n

上述为已讨论候选，不表示都已采用或已验证。烟火候选与引擎的 AGPL 条件须在实际引入时保留；参考 PPT 和私密内容不放进源代码包。演示视频、课程图片和题目记录来源和审核状态，不虚构指标。
