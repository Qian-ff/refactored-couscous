# 开工与交接

A1三端共享底座与checkpoint-1保留历史；B1、既有UI及云端API/ASR前置现已通过A集成验收，真实契约0.3.2。当前C开工基线为[c-start-ready](cloud-asr-handoff.md)，完整SHA以git rev-parse核验；C允许执行，B2仍等C交付后另行放行。Open-DUI.cmd打开现有网页，Start-CloudASR.cmd恢复本机识别节点；A0/A1历史证据与当前阶段分开，统一顺序见[a2-start](a2-start.md)。

a2-ready、b1-ready和各UI设计/组件标签保留历史，D第二批已交付，不重复运行旧Goal。后续仍按A环境放行→C→B2联合验证→D后续接入→A2。任务书见[ai入口](ai/README.md)，环境按[共享环境](shared-environment.md)复用。D唯一正式入口路由，不同时启动所有业务Goal。

~~~powershell
python .\others\scripts\workflow.py status --baseline a2-ready
python .\others\scripts\check_preparation.py
python .\others\scripts\shared_env.py probe
~~~

准备检查只证明文件、归属和工具一致。业务/网页/原生/语音的已实现、实测、计划分别记录；完整搜索、题库考试、原生录音与A2包尚待后续。每轮相关检查后本地commit，不覆盖他人改动。A0不额外推送，A2重建入口/客户端及九组合真实验收后才按授权checkpoint-2，E/F后续扩展监控和正式发布，G独立验收。
