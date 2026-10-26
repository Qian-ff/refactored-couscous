# 多工作树共用本机环境

## C1 T2独立候选

active `c1-runtime-public-integration` 下，A副仅用本树 `others/runtime/c1-public/envs/{backend,worker}`，由 `python others/scripts/c1_candidate_env.py prepare --surface backend` / `--surface worker` 准备；只复用主树解释器和缓存，不覆盖共享venv。helper每次核对分支、已提交授权祖先、锁与描述指纹，pytest仍持共享串行锁、固定safelab_c1_test profile。正式共享环境待A接收后激活，不能拿候选新锁调用旧shared_env强行绕过不匹配检查。

backend生产依赖不加Excel，dev才用openpyxl3.1.5/defusedxml0.7.1；worker增加这两项及pydantic2.13.4，锁定传递依赖、官方wheel哈希和许可，保留原语音/资料解析版本。构建只复制14包解析/传输闭包，不复制整个worker、SQLModel、API配置、模型或密钥；候选缓存官方Linux wheel哈希核对后离线安装。

API8002/控制18768及其存储/任务/运行日志均在c1-public；main8000/5173/18767和原库独立。C1命令/配置、实际通过与未验边界见 [C1公共交接](c1-public-handoff.md)。

现行职责见[统一协作规范](coordination.md)。A副复用主树依赖/配置/模型，但app_source、worker_source、Git提交和报告属于本树；共享测试库仍串行锁定，不能用主树服务证明分支新代码。

统一入口通过 Git common directory 定位主工作区，不把个人路径写进公共配置。配置/依赖共享，源码/报告/Git分支分别属于各树。

| 内容 | 规则 |
|---|---|
| .env、本机设置、合成账号 | 主树一份；子进程加载，不输出密钥；账号读取common-root/others/runtime/demo-accounts.json |
| 业务Python | 主树others/backend/.venv，项目缓存CPython3.14.6，锁文件含测试工具；A唯一维护 |
| 语音worker | 主树others/ai_worker/.venv，项目缓存CPython3.13.16、sherpa-onnx/core均1.13.8、numpy2.4.4；与业务分离 |
| 模型 | 主树others/models/paraformer-2023-09-14一份；固定来源/哈希见worker/models.lock.json |
| 前端包 | 主树others/cache/pnpm-store，各树node_modules离线硬链接；各自缓存/输出，禁止编辑包文件 |
| pnpm CLI | 主树others/cache/tools/pnpm/11.25.0；A维护、官方包完整性校验，Use-ProjectEnvironment仅加入当前shell PATH |
| uv/Gradle/Electron | 主树忽略缓存，设置仅会话级；不改系统Python/JDK |
| 源码/测试报告/构建 | 当前树；正式客户端由A集成后重新构建 |

## 各树入口

~~~powershell
. .\others\scripts\Use-ProjectEnvironment.ps1
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
python .\others\scripts\shared_env.py install-web
pnpm run check
pnpm run build:web
~~~

probe必须输出共享解释器及**本树**app_source。依赖描述/锁与主树不同即拒绝复用，先交A更新，不在B/C/D运行Bootstrap或uv sync。install-web只离线硬链接，缺包明确失败；已有依赖无需每轮重装，不为子树复制虚拟环境。

~~~powershell
python .\others\scripts\shared_env.py backend pytest -q --tb=short
python .\others\scripts\shared_env.py probe-worker
python .\others\scripts\shared_env.py worker speech.实际模块
~~~

worker命令只接受当前树others/ai_worker内的实际模块。A已提供transport/私有真实ASR及进程取消/超时，各树业务通过app.core.asr_client消费主树忽略配置，见[云端ASR交接](cloud-asr-handoff.md)；C新增content/、speech/仍运行本树源码。worker入口设置LABCONNECT_SHARED_ROOT和LABCONNECT_MODEL_ROOT，模型一份；没有业务.env或云AI密钥直通给worker。A主决定共享服务/SSH通道维护，A副仅按明确工作包执行，子树不另起占用18765的实例。

所有共享pytest入口使用同一个本机专用测试库且加跨进程锁，冲突明确拒绝，稍后重试；不并行互删表，不用演示库测试。根others/backend/conftest.py覆盖tests及app/domains，领域夹具已以真实PG验证。测试命令用--tb=short避免驱动栈局部变量暴露配置；报告也不保存密钥。需要独立并行测试库先由A分配。

contracts.py的OpenAPI导出复用共享解释器并显式绑定当前工作树，先核对后台依赖锁，不要求本树.venv。B合并公共0.3.0基线后可执行python others/scripts/contracts.py check；未同步时若领域源码与旧契约不一致会如实失败，不以A的导出冒充B结果。

## 端口与来源

A主/B/C/D前端分别5173/5174/5175/5176；A副前端5177、独立API8002，Vite按分支选择、strictPort。D通常连接A的8000 API；B/C分支API可选空闲8001等并先协调迁移，不能拿A已发布服务冒称分支新接口。

~~~powershell
.\others\scripts\Start-Backend.ps1 -Port 8001
python .\others\scripts\provenance.py --surface api --verify-url http://127.0.0.1:8001
pnpm run test:web
~~~

Playwright从common-root读合成账号；globalSetup检查网页为本树、API默认主树，各自SHA/树哈希/源码内容指纹/契约必须匹配。其他真实API可设置LABCONNECT_API_ROOT和LABCONNECT_API_URL，额外前端端口LABCONNECT_WEB_PORT须先由A配置CORS并检查。不能只因端口响应或标题相同复用。元信息捕获于启动；提交/代码改变后旧服务可能失效，先核对并重启自己拥有的服务，不停别人的进程。正式包只记录SHA/指纹/契约，无本机路径；API生产环境不挂dev/identity。

浏览器验收可设置LABCONNECT_REPORT_STAGE=b1-public等阶段名称，将报告和截图保存到当前树others/reports/对应阶段，避免覆盖历史证据；不设置仍写a0。名称只允许字母、数字、下划线和连字符，不接受路径。

启动网页使用原Open-Web.cmd或Start-A1.ps1 -Target Web。它检查API/网页归属，遇忙端口且版本不匹配会保留服务并拒绝。主树迁移从共享入口运行，不偷偷重置账号或数据库。各树共用演示数据会互相可见，只用合成账号。

## A维护与重新建立

Codex运行时刷新后若pnpm消失，A在主树执行python others/scripts/prepare_pnpm.py；固定来源、11.25.0版本、SHA512与许可记录在others/config/toolchain.json，不执行远程安装脚本、生命周期脚本、全局安装或Corepack切换。随后重新点载Use-ProjectEnvironment.ps1。各树合并本轮公共依赖后点载自己的同名脚本，即复用主树CLI，不复制工具环境。python others/scripts/prepare_pnpm.py --check可离线核验已安装文件；缺失或不完整明确失败并保留现场，不擅自覆盖。当前项目Node要求仍为package.json中的>=24.14.0 <25。

业务用Bootstrap.ps1，锁定uv与项目内CPython3.14.6，uv sync --frozen --all-groups。旧环境已保留于主树others/backups；不修改原D盘解释器。语音用Prepare-Worker.ps1（见worker README），模型可续传，下载后核验哈希/许可并实测公开音频；不装到业务环境。

本机受限Codex进程中，Windows卷路径解析被拒绝：文件可打开而GetFinalPathNameByHandleW的DOS/GUID卷查询报WinError5，使CPython启动报告“Failed to find real location”，Node/pnpm也可能realpath EPERM。新旧/项目内Python均可复现；正常授权进程无该警告。已通过项目内运行时去除对外部解释器位置的依赖，**未宣称修复外部沙箱权限**；真实联网/数据库/Node检查在正常授权进程运行，保留stderr，不补丁CPython、不放宽系统安全设置。
依据：[CPython getpath](https://github.com/python/cpython/blob/v3.14.6/Modules/getpath.py#L377-L386)、[Windows路径查询](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)。

本轮证据和未完成边界见[a0-handoff.md](a0-handoff.md)，不能把环境准备当成三端语音验收。

## A副独立验证入口

在登记的A副树先运行shared_env.py status/probe/probe-worker；已有依赖不重装。需要网页依赖时用install-web离线复用。API使用Start-Backend.ps1 -Port 8002；网页按codex/a-executor分支默认5177。端口占用或源码身份不符则保留已有服务并报告，不终止其他树进程。浏览器验证显式设置LABCONNECT_API_ROOT为本树、LABCONNECT_API_URL为http://127.0.0.1:8002，避免默认主树API产生假通过。Start-A1仅用于既有主/业务树，A副使用上述分支独立验证入口，不执行演示库迁移。
