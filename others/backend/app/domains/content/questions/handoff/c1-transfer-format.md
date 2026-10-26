# C1题目交换模板候选

实现：`questions/transfer_codec.py`、`questions/transfer_cli.py`、`questions/imports.py`。已提供无数据库编解码、固定CLI和领域内的预检入库/原子确认候选；不证明上传、排队、真实PG确认入库、授权导出、真实沙箱或清理已完成。可信控制端和公共接口接入仍待交付。

## 模板

CSV采用UTF-8（接受BOM，导出带BOM）；XLSX只有名为`Questions`的一个工作表。前两行分别为：

1. 第一格`labconnect.question-transfer/1`，第二格文本模式，其余最多六格为空。
2. 精确列名：`kind,stem,options_json,answer_ids_json,explanation,knowledge_points_json,difficulty,provenance_json`。

数据从第三行开始，恰好八列、最多1000题。kind为single/multiple/true_false/scenario；difficulty为easy/medium/hard。options_json为选项对象数组，answer_ids_json和knowledge_points_json为字符串数组；provenance_json对应严格Provenance模型，不允许夹带审批、发布或服务端来源证明字段。

`literal-text-v1`便于人工填写普通文本，禁止以空白加`= + - @`开头的单元格。`escaped-text-v1`用于导出：每个数据单元格固定增加一个英文单引号，导入按模式精确去掉一个，原本的单引号不会丢失。导出的中文、逗号、换行、引号和公式样式文本均能无损回导；CSV引用规则本身不足以防止电子表格执行公式，因此不能删除转义标记。XLSX要求文本单元格，公式即使有缓存值也拒绝。

此模板不携带MaterialVersion/SourceChunk权限。授权导出服务须先逐版本鉴权，投影移除不可移植的材料指针，同时保留真实许可元数据；不能把跨校模板导入当作原始私有资料授权。存在来源指针的原始DraftContent不能直接调用导出函数。

## 边界及错误

- CSV输入1MiB、XLSX输入5MiB，解包实际读取总量16MiB，预检输出16MiB；导出受同格式输入上限约束，以保证可回导。大集合应由调用方分批，不能静默截断。
- 严格列、行、单元格和题目模型检查。预检逐行只返回规范化待审核内容、错误代码及批内重复行号，不回显失败行原文或异常堆栈。与既有题目的重复检查仍须服务端按当前权限执行。
- XLSX在打开库之前遍历实际ZIP流；拒绝非模板组成文件、重复名称、路径穿越/宏、加密、非允许压缩、危险XML、外链、公式、超范围行列；所有XML（包括元数据）均检查，不只检查工作表。
- XLSX真实读写要求openpyxl 3.1.5且启用defusedxml；缺失或设置不符明确`xlsx_dependency_unavailable`，不降级为不安全XML解析。完整锁定/依赖许可由A副2按委托处理。
- 编解码不读取数据库/AI配置。它不自行提供30秒硬超时、384MiB内存、无网/非root/只读根等隔离；这些属于可信runner。openpyxl写出会使用临时存储，必须定向到任务计量目录，由A副2验证32MiB预留峰值、失败残留和确认清理，不能声称纯测试已证明配额。

## 已执行证据

`test_transfer_codec.py`包含CSV往返/公式文本/冲突答案重复、错误脱敏、格式/编码/大小/行数边界、ZIP实际解包大小、路径/宏/外链、危险XML/公式/超范围单元格测试。真实XLSX往返检查在缺指定依赖时明确skip；skip不算格式可用证明。下一阶段须在A副2真实技术SHA复核XLSX、上传确认/原子回滚、授权导出、配额、取消/重启和沙箱。

## 固定CLI与预检确认接缝

可信runner只允许以下固定模块命令，输入固定挂载`/job/input`，不接受HTTP传入命令、路径或镜像：

```
python -m app.domains.content.questions.transfer_cli --operation import --format csv
python -m app.domains.content.questions.transfer_cli --operation import --format xlsx
python -m app.domains.content.questions.transfer_cli --operation export --format csv
python -m app.domains.content.questions.transfer_cli --operation export --format xlsx
```

import输入为实际文件字节，stdout为严格Preview JSON；export输入为`{"protocol":"labconnect.question-transfer/1","questions":[DraftContent...]}`的有界JSON，stdout为文件字节。退出0才可消费结果；失败退出1，stdout仅含协议和脱敏error_code，不输出堆栈。固定CLI不加载dotenv、数据库或AI设置。A副2须把本包及纯输入模型纳入受限镜像，并锁定依赖，不在普通API请求进程直接运行解析。

`ingest_preview`仅供可信控制端的事务调用：先读取固定runner实际有界输出并严格解析，校验generation/execution_id/lease_owner/租约/状态/输入指纹，重载真实登录/角色和目标授权；在当前可读草稿内检查重复后记录批次与绑定指纹。它不提交事务，也不释放任务预留；调用方须明确提交/回滚、确认进程停止及清理。迟到结果、替换执行、取消、撤权或过期不能落为ready。对已取消任务的存储回收仍由控制端处理。

`confirm_import`重验真实会话、目标库、revision、原件hash、预检hash及任务状态，重新查有权重复题；全部通过才一次批量创建待审核Question/QuestionDraft与结果映射，并执行公共统一配额检查。任一错误整笔回滚；幂等重放仍鉴权，命令回执只含batch_id/state/revision/count，无题干或答案。结果ID经重新授权后分页读取；未通过预检的批次不支持跳过错误或覆盖旧题，须更正文件重新预检。

纯检查验证了篡改指纹/内容/目标/代次/状态与未知结果字段被拒绝，以及固定worker处理函数的CSV导出→预检往返。真实PG原子回滚、幂等及重复竞争候选在`tests/pg/test_imports.py`，尚未运行。上传/队列共用、stop-before-start、失败恢复、真实HTTP及导出下载再鉴权仍为后续必需工作。

## 持久任务命令候选

`transfers.py`提供创建导入/导出、任务安全状态、取消、显式重试、导出执行时私有输入和下载前存储票据；尚未挂载HTTP或真实runner。TransferAdmission为A提供的统一准入检查，缺失明确503；不得用测试的SEMANTIC_ADMISSION替代正式队列。它必须在同一个quota_lock下检查C02与C1的统一队列、owner上限和跨模块接收槽；C没有建立第二套免费队列。

导入仅创建批次/接收任务和32MiB预留，待真实流上传校验封存后才能设`input_sealed=true`并入队。导出固定有序ExportVersion清单与规范化输入hash，原始材料指针不外带，许可/来源链逐项验证。worker执行时重新鉴权并重算同一输入hash，不自动选择latest。清单ordinal具有唯一及0..999约束。文件key由服务端task UUID生成，不接收客户端路径。

取消递增generation，保留预留，等待可信控制端停止与清理；已预检但未确认的批次也可取消，已生成草稿的历史确认不能取消。重试仅允许failed/canceled、原代次一致、stop_confirmed且reserved_bytes为0；导入还须原件仍真实封存。重试重新做统一准入/配额及当前授权，清空旧预检结果并重新排队，不重用旧execution_id。旧执行不可在重试后回写结果。过期任务须新建，不通过重试无限延长。

导出下载票据只供可信流传输适配，不是公开JSON DTO；不提供静态目录/裸文件key下载。取得票据前重新检查真实会话和清单中每个固定版本读取权、来源停用状态及结果边界，发送过程中仍须使用新Session定期再次鉴权，结束时校验真实长度/hash。流式上传下载已在streaming.py提供候选，本地真实文件I/O配合覆盖的DB回调验证了长度/hash封存与下载跨块撤权；真实PG/公共HTTP及runner导出结果落盘仍待A副2接入验证。

新增纯检查覆盖准入缺失、输入边界、重试停止/清理/原件/代次条件、无效下载结果；PG候选覆盖缺准入不写库、取消不释放预留、导出任务不能恢复已停用来源的读取权，尚未运行。这些不证明统一队列/真实沙箱或实际存储清理通过。
