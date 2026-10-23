# C-02 解析候选（M1进行中）

本目录不加载业务配置、数据库或AI模型。仅由A的固定受限执行模板运行不可信输入；本机共享worker只用于可信合成夹具。当前没有受限适配器，不能用普通子进程替代上传链路。

## CLI边界

`python -m content.cli --input <本任务只读输入> --format pdf|pptx|docx|txt|text [--encoding utf-8|gb18030]`

输入路径只能由受信运行适配器分配，不接受公开HTTP路径参数。成功退出0并向stdout写一个`labconnect.parse/1` JSON，失败退出1并返回安全`error_code`；A仍须在读取stdout过程中执行16MiB硬上限、stderr64KiB、60秒截止和完整执行单元回收。CLI本身不是文件系统或进程沙箱。

结果包含format、parser_version、chunks和warnings；chunk含ordinal、locator(kind/position/part)、text和SHA256 text_hash。position从1开始且保留源页/幻灯片/段落，part是该位置内8192字符分片序号。空段不造正文，后续位置不压缩。原输入哈希与MaterialVersion由业务层保留。文字只作文字渲染。

## 依赖交A锁定

|候选|来源|许可|
|---|---|---|
|pypdf 6.21.2|https://pypi.org/project/pypdf/6.21.2/|BSD-3-Clause|
|python-docx 1.2.0|https://pypi.org/project/python-docx/1.2.0/|MIT|
|python-pptx 1.0.2|https://pypi.org/project/python-pptx/1.0.2/|MIT|
|lxml 6.1.3|https://pypi.org/project/lxml/6.1.3/|BSD-3-Clause及发行包第三方声明|

A负责传递锁、发行包哈希、全部第三方声明、固定容器镜像及Windows/Linux实际兼容检查。本目录没有安装依赖或修改公共锁。四格式正常夹具及版本矩阵待依赖接入后补齐，不因代码存在宣称通过。

## 当前验证

`shared_env.py worker content.verify --report <本树忽略区报告>`运行当前可信合成测试并记录依赖现状。缺依赖仍退出1；report明确`sandbox_verified=false`和`four_format_integration_verified=false`。目前是TXT正常解析、结果协议及恶意OOXML预检，不是完整解析验收。A受限入口接入后还须补足四格式正常样本和资源/取消/隔离实测。

夹具全部由测试现场生成，不使用真实课件或私密参考PPT。
