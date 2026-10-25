# C1题目交换模板候选

实现：`questions/transfer_codec.py`。这里只提供无数据库编解码；不证明上传、排队、确认入库、授权导出、真实沙箱或清理已完成。固定CLI及可信控制端接缝仍待交付。

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
