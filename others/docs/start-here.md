# 开工与交接

A1最初三端共享底座与checkpoint-1保留，历史证据见[a1-handoff](a1-handoff.md)。当前为[B1集成交接](b1-handoff.md)，真实契约0.3.1，后续接C；A0历史证据见[a0-handoff](a0-handoff.md)，当前基线/分支与顺序见[a2-start](a2-start.md)。

固定顺序为A0→B1→C→B2联合验证→D→A2。a2-ready保留A0历史；C在A发布b1-ready后保留自己的改动并合并该完整SHA，以后继续按A每阶段真实公共集成SHA接续。任务书见[ai入口](ai/README.md)，配置和依赖按[共享环境](shared-environment.md)复用。每次接口/迁移及时交A，D唯一正式入口路由；不同时启动所有业务Goal。

~~~powershell
python .\others\scripts\workflow.py status --baseline a2-ready
python .\others\scripts\check_preparation.py
python .\others\scripts\shared_env.py probe
~~~

准备检查只证明文件、归属和工具一致。业务/网页/原生/语音的已实现、实测、计划分别记录；完整搜索、题库考试、原生录音与A2包尚待后续。每轮相关检查后本地commit，不覆盖他人改动。A0不额外推送，A2重建入口/客户端及九组合真实验收后才按授权checkpoint-2，E/F后续扩展监控和正式发布，G独立验收。
