# C1：题库、固定关卡版本与受控内容服务

状态：用户已确认本聊天最终计划并手动启动完整实施。M1仅为候选，不是C1整包完成。

## 核验与执行范围

- C / host local / thread 01a15942-9518-7660-a13c-6b5711d08ef6。
- 工作树 D:/codex/worktree/ffb2/SafeLabPlatform，分支 codex/c-content-ai-a2。
- 开工HEAD ecb7129497d1f6a69daf09df6db3f2f30537d7ba，工作区/暂存区干净。
- 指定执行基线 3cdb38310e2c4fbd8a514384b6670062752ef1eb；保存本计划并提交后普通合并，不跟随移动main。
- 实际轮次已核验 Default / gpt-6.1-sol / medium；不修改全局设置。
- 只新增 content/questions/ 和 content/lessons/，测试、合成夹具、提案和交接留在各自模块；原C02顶层/worker由A副独占，不恢复旧任务。
- 公共注册、迁移、配额、依赖、控制端、总路由及SDK归A/A副2；B负责正式学习/考试，D负责全部前端。

## 结果与已锁规则

复用Library、B当前Identity、R/S/V策略、先授权SQL、短命令/幂等/revision/审计。学校、学院、目录、班级及平台公共分别授权；不另建组织体系，不强制班级学院等于目录学院。

Question、QuestionDraft、QuestionVersion分开：草稿可改，提审冻结版本；保留来源、复制谱系、独立审核及发布绑定。Lesson、LessonDraft、LessonVersion同构，活动评分载荷与学生投影分离；Scene/SVG资产ID、哈希、许可和版本不可覆盖。需要用题库时保存真实question_version_id，Material ContentRef不得改作题目/关卡引用。

创建草稿须S；读草稿须真实R；改删须R且本人S或范围V。整库管理用V。审核决定只读，复制不继承审批；来源已发布R+目标S+许可才可引用/复制，不授予原件权限或穿透私库。发布固定版本与目标；停用阻止新选用，保留旧快照。查询先授权后筛选/计数/分页，详情/结果再次鉴权。回执只存最小ID/状态，重放重新鉴权。

提供题库/关卡列表、关键词和知识点筛选、手动草稿增删改、固定版本、提审/决定/发布/停用、引用/复制。题型single/multiple/true_false/scenario；关卡choice/hotspot/order。所有引用、状态和payload以服务端类型校验及真实FK保护。

## 接口和消费

向B2提供Python服务端受控版本读取：真实身份、教学班、确切版本ID；返回固定内容、私有答案/评分数据/hash及授权结果。禁止自动latest、用户purpose提权或公开答案接口。B2发布时固定内容、评分与素材版本快照；正式作答/解锁/判分/记录归B2。

StudentLesson严格沿用labconnect.lesson/1，无答案、评分配置、私有评分hash、正确顺序或隐含标记。TeacherLessonPreview独立，范围鉴权且不写正式学习记录。来源逐条鉴权。正式学生JSON和场景素材均由B2检查同一任务/版本/解锁后读取，不用裸asset_id、hash或普通R绕过。

C给D教师编辑/预览及状态/错误/资源接缝说明，不导入D组件/路由。安全SVG白名单拒绝脚本、事件、foreignObject、外部URL及主动资源，资产不可覆盖删除破坏历史。

## CSV/XLSX与样例（用户本轮明确选择）

C1一起交CSV/XLSX预检、确认生成待审核草稿、授权导出；通识/化学各约30道，共约60道去重草稿。六主题为入室防护、设备用电、应急处置、试剂标签储存、操作通风、废物泄漏；两个示范班各三关，数量数据驱动。交短课、原创二维SVG、互动样例及来源。所有示范题/课保持待审核，不伪造专业教师批准；测试审核发布仅使用标识清楚的合成数据。

来源保存URL、作者、许可/许可URL、获取日期、原文版本/hash及改编说明，区分原创、改编和原题。不读取私密PPT，不调用云AI，不虚构官方题库或教师背书。

独立ImportBatch/TransferTask，不伪造Material关联。流程：批次预留→有界上传→受限预检→分页错误/重复→绑定目标、内容/预检hash和revision确认→短事务重验并原子生成草稿；未通过不提交，不覆盖已有题。导出当前有权固定版本，结果下载再鉴权、防公式注入、有界输出，并验证模板回导。

纯CLI与版本化labconnect.question-transfer/1协议在questions内，不读DB/AI配置。A副2按具体委托扩展既有封闭控制端，不新增任意命令/路径/镜像或新部署。CSV1MiB，XLSX5MiB，单模板工作表，最多1000题，实际ZIP展开总量16MiB，输出16MiB，解析30秒；行/列/单元格/文本均有界。拒绝路径穿越、加密、宏、外链、公式及危险XML，不读公式缓存冒充无公式。

沿用384MiB、CPU1、pids64、tmpfs64MiB、无网、非root、只读根等隔离。候选依赖openpyxl3.1.5+defusedxml0.7.1，由A锁完整传递依赖/hash/许可并实测；安装防XML包不代替ZIP/资源边界。

资料/导入/导出共用全局队列、接收槽、重任务排他、持久execution_id/generation、stop-before-start和确认清理。原件、预检、草稿、导出、SVG、临时副本及残留纳入同一学校/公共/全局计量，32MiB任务预留须证明峰值，不能暗增或漏计。5MiB上传由A配置准确导入路径流式上限/网关例外，不放宽整个content。

## 分段接入：A已只读采用，不重复整包审批

1. C交领域M1候选、纯检查、CLI、模型/迁移/计量/路由提案及冻结SHA，准确列出未跑项。
2. A副2获具体委托后在独立集成树接迁移、非owner专用PG、受限任务种类、配额及实际SDK，公布候选技术SHA。其输入是M1，不等C1先跑完全部PG。
3. C按准确技术SHA补真实领域PG并修自有模块；A副2补公共HTTP/SDK/旧功能回归。
4. A接收后发布B2/D2真实基线。C1完成须领域、CSV/XLSX、样例、必要真实PG/集成及交接齐备；M1不冒充完成。不自动启动C2/C3，不自行push或发布。

## 检查与证据

纯检查/Ruff先行；迁移/非owner测试入口由A提供后，专用真实PG串行运行。覆盖五范围/跨校学院/双班/撤权、计数分页/直链、并发编辑审核导入/幂等/原子回滚、固定版本历史、学生DTO/排序/SVG/引用/导出泄漏，以及格式攻击/公式注入/超限/取消/重启/迟到执行/清理故障/配额竞争。

计划命令（新模块存在且阶段满足后执行）：

```powershell
python .\others\scripts\shared_env.py status
python .\others\scripts\shared_env.py probe
python .\others\scripts\shared_env.py backend ruff check app/domains/content/questions app/domains/content/lessons
python .\others\scripts\shared_env.py backend pytest app/domains/content/questions/tests app/domains/content/lessons/tests -q --tb=short
```

领域证据在模块内已忽略test-results/c1/，记录SHA、源码、解释器、contract/migration、退出码和未跑项。每轮仅暂存本轮自有文件并本地commit，无差异不空提交。里程碑一次简报A；停工/结束handoff写系统临时目录。不得改系统配置、伪报缺依赖/跳过/未验通过或以SQLite替代PG。
