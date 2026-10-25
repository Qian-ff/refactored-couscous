# C02后台候选接收审查：e43da754

2026-10-25，A主/main审查`e43da75468b9834011d1342b9a8f78f289ee7711`。本变更提供资料后台、迁移、非owner运行角色、受限解析控制端、真实0.4.0 API/SDK和测试入口；当前预期规模为100账号、20普通请求并发，重任务全局排他。**先修下列两项，暂不合入main、不发布给D。**

## 已核验

- 109个差异文件均在现有具体委托白名单范围内；保留冻结C候选及合并历史。
- A实际请求本机8002：dev identity为候选完整SHA、契约0.4.0；health为PostgreSQL、迁移`c02d0c00001`。
- 已实际核对final-manifest索引的31个附件哈希，无不一致。A副报告152后端测试及55 subtests、18四格式、4 ASR传输和5最终浏览器等证据；这些测试不能证明下述未覆盖边界安全。
- 只读审查了控制端/传输适配/容器入口、资料动作与按目标投影、部分迁移/角色及相关调用路径。尚未独立重跑全部业务/三端，Linux控制端生产部署、共享环境激活和ECS均未完成。

## 必须修复

### 1. 任务结果可通过符号链接读取目录外文件

位置：候选`others/deploy/content/control.py`的`inspect_locked`与`handle(result)`。前者用`is_file/stat/read_text`信任status/result，后者直接`open(result.json)`；这些调用会跟随符号链接。隔离解析器可写自己的输出目录，该目录内容必须按不可信处理。

复现使用候选控制端真实源码，在已缓存Linux镜像内建立合成任务目录与目录外的合成合法解析JSON，将任务`result.json`指向该文件；仅用桩表示容器已退出，不调用或改动现有Docker控制服务。候选`handle(result)`返回了目录外JSON内容：

~~~json
{"scope":"isolated-synthetic-output-boundary","result_is_symlink":true,"outside_result_followed":true,"real_services_changed":false}
~~~

这是不可信输出到受信主机读取的边界缺口，不是已经观察到真实课件/密钥泄漏。最小修复是统一安全打开已退出任务的输出文件：检查常规文件，拒绝符号链接/Windows重解析点、硬链接及FIFO/设备等特殊文件；读取使用经校验的同一文件句柄、限制字节量并防止替换。status、accepted及result等控制端消费的不可信标记均核对；无法安全验证时返回不可用。继续保持结果流与release互斥、实际停止和清理确认。

需要回归：正常结果仍成功；链接到任务外合法解析JSON、status链接、硬链接及特殊文件被拒绝且不返回合成私有标记；Linux与Windows适用路径分别有证据，拒绝用“多做一次resolve”代替安全读取。

## 应修复

### 2. Docker命令输出分片时被截断

位置：同文件`docker_call`内部`bounded`。单次`await stream.read(FRAME + 1)`允许在EOF前返回部分数据；随后仅等待进程退出，剩余输出没有消费。完整Docker inspect/错误JSON可能变成残片，造成正常执行被误判不可用或恢复失败。

隔离测试仅把该函数的子进程替换成分两次输出合法JSON的Python进程，使用候选方法本身；没有调用现有服务。应收11字节，实际仅收到1字节：

~~~json
{"scope":"isolated-fragmented-subprocess-output","expected_bytes":11,"actual_bytes":1,"complete_output":false,"real_services_changed":false}
~~~

最小修复：stdout/stderr各自循环读到EOF，累计上限仍为FRAME，超限/超时终止并回收进程，不无界capture或丢失stderr。回归覆盖分片stdout、分片stderr、超限与超时，保留“确认不存在”和Docker不可用的区分。

## 接棒与完成边界

这两项由A副在现有`c02-public-integration`中修复，控制端和同目录回归测试已属委托范围，不新增包、不改共享环境。仅暂存本轮相关文件本地commit，交新完整SHA、必要回归及更新后的最终来源/证据索引给A；不合main、不推送或提前启动A副2。

A的隔离复现脚本位于主树忽略区`others/runtime/c02-review/probe_output_links.py`和`probe_docker_stream.py`，复制的源码固定来自e43da754；仅复制三个必要源码，不含配置/账号/课件。命令使用已缓存镜像、无网、只读、128MiB内存及隔离tmpfs，未改变实际服务。长期回归由A副放入其已授权控制端测试范围，不能只保留忽略区复现。

结论：修复1和2后再接收。原候选的纯检查、PG/HTTP和资源实跑证据保留；新代码变化所影响的检查及最终SHA来源需重新证明。C02整包、D真实闭环、共享激活、main三端和ECS仍分别验收。
