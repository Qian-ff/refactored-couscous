# 独立内容与语音 worker

A0准备本项目独立Python3.13.16、sherpa-onnx1.13.8及同版本sherpa-onnx-core、numpy2.4.4 CPU环境，精确依赖/平台wheel哈希在uv.lock。业务服务继续Python3.14，B/D不安装worker，所有树共享主树环境与模型缓存，各树绑定自己的worker源码。A补充transport/私有真实ASR传输与进程生命周期，部署/验证及C消费见[云端ASR交接](../docs/cloud-asr-handoff.md)。C接续实现content/、speech/业务，E后续监控；没有假成功推理HTTP接口。

A在主树重新准备：

~~~powershell
.\others\scripts\Prepare-Worker.ps1
python .\others\scripts\shared_env.py probe-worker
~~~

Prepare-Worker只安装项目缓存解释器与锁定环境，模型固定版本可续传、核验哈希/许可，真实识别公开test_wavs/0.wav，报告others/reports/a0/speech.json。模型来源/哈希见models.lock.json；权重在忽略others/models，一份缓存。来源与许可证据归档others/licenses/paraformer，不把权重、录音或环境打包进客户端。

Windows曾因uv遗漏主包声明的core，误加载旧ORT1.17.1而崩溃。显式精确锁定sherpa-onnx-core==1.13.8提供匹配本地DLL，不改System32；复现及解决依据见[官方issue3059](https://github.com/k2-fsa/sherpa-onnx/issues/3059)。识别是否通过以[a0-handoff](../docs/a0-handoff.md)的实际结果为准。

C运行实际本树模块用shared_env.py worker speech.模块名；入口验证模块路径属于本树，设置共享模型根。音频协议/页面参数/考试限制见../contracts/a2-protocols.md。完整三端点击录音、权限、格式转换、中文确认问答/播报还需C/D交付后A/F适配；公开WAV示例通过不代表三端链路通过。原录音默认处理后删除，原始监控媒体只存校内/本地。
