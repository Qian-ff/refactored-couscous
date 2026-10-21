# 开源与素材要求

用户允许按适用条款交付组件。A1固定FastAPI模板及Electron/Capacitor来源见upstream.md；A0新增精确React Router、cryptography及独立sherpa-onnx/core CPU语音运行时，锁文件及others/licenses归档许可。模型权重只在忽略缓存，不进入Git或客户端。

others/licenses 保存模板 MIT 原文、实际前端运行依赖的许可文本与版本来源清单；运行 `node others/scripts/licenses.mjs` 从已安装依赖更新。文本随网页 dist/licenses、Windows 资源及安卓网页资源交付。Python 完整依赖由 uv.lock 固定，安装后的发行包保留其自带 dist-info 许可。Electron 包另保留 Chromium 自带许可。

D-UI正式采用未修改的Noto Sans SC可变字体，固定google/fonts提交a85815a42757630ce188fdad368c2dfc444d4773；字体SHA256 a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da。SIL OFL 1.1原文及上游来源逐字节归档为others/licenses/noto-sans-sc-OFL-1.1.txt、noto-sans-sc-source.json；产品资源另保留原OFL，字体从包内加载，原始设计冻结资料不改写。

云端网关采用官方Caddy 2.11.7-alpine，Python/PostgreSQL/Caddy镜像摘要固定在[云端镜像锁](../deploy/cloud/images.lock.json)。Caddy源码来自https://github.com/caddyserver/caddy/releases/tag/v2.11.7，Apache-2.0原文归档于others/licenses/caddy-Apache-2.0.txt（SHA256 cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30）；随共享网页许可目录分发。官方基础镜像内置系统包及其许可保留，云端包不含本机模型、账号或私密参考材料。

框架接入时逐项记录：名称、固定版本/提交、原始 URL、代码许可、权重许可、素材许可、修改及分发要求。代码许可不能替代模型或素材许可。完整许可证与 NOTICE 随适用组件交付。

选型来源：
- https://github.com/fastapi/full-stack-fastapi-template
- https://github.com/electron/electron
- https://github.com/ionic-team/capacitor
- https://github.com/SYSTRAN/faster-whisper
- https://huggingface.co/rabahdev/fire-smoke-yolov8n

上述监控/其他ASR为讨论候选，不表示采用。当前ASR选csukuangfj/sherpa-onnx-paraformer-zh-2023-09-14固定提交，来源、Apache-2.0声明及文件哈希见../ai_worker/models.lock.json和../licenses/paraformer，实际示例识别见a0-handoff.md。python_licenses.py从锁定wheel归档cryptography、sherpa-onnx/core、numpy许可及来源；代码许可与模型许可分别记录。烟火候选与引擎AGPL条件引入时另核对；私密PPT不分发，课程图片和题目保留来源审核，不虚构指标。
