# Git 与多聊天工作区

现行角色、工作包、汇报/handoff和自动调度见[统一协作规范](coordination.md)。A副以--executor A-executor登记，checkpoint还须--package已批准包编号；不使用--role A。A主仍唯一接收main与发布基线。

用户要求：每轮代码生成或修改结束保存本地提交，分支聊天提交自己的分支。仓库规则由根 AGENTS.md 生效；此文给出操作步骤。

## 分支与工作区

A 使用主目录 main；角色分支由 ownership.json 指定。B/C/D 使用用户新建的外部 Codex 工作树及 codex/*-a2 分支，由 A 登记；G按需使用原验收分支；E/F旧树与分支仅历史保留，A副用独立codex/a-executor分支。工作区之间共享 Git 历史，各自修改自己的源码。最多同时运行四个聊天。当前基线、顺序见 [A2 开工](a2-start.md)，配置和依赖见 [共享环境](shared-environment.md)。

临时设计任务由A记录在[auxiliary-tasks.json](../contracts/auxiliary-tasks.json)，不充当当前业务或A副身份。ui-design-v1已使用codex/ui-design-v1和others/worktrees/ui-design，只可提交others/design/ui-redesign/。每轮在该树核对实际目录、分支和暂存范围，显式逐文件git add后commit，不借用workflow.py的A/D身份。A按main...候选SHA核对差异；用户网页批准及完整规范冻结后才接收设计提交，详见[批准门禁](ui-redesign-coordination.md)。

用户已新建的外部工作树由 A 在干净、已提交规则的主目录执行登记，例如：

~~~powershell
python .\others\scripts\workflow.py register --role B --path "实际的B工作树绝对路径" --baseline 825b6e3
~~~

登记检查同一仓库、干净状态、指定祖先基线和分支占用；仅为 detached 树创建角色分支，不覆盖旧分支历史，不自动合并。A 再将三个新树快进同步到 a2-start。已登记 B/C/D 的 worktree 命令只报告现状；不会重新创建另一份目录。尚未启用的托管工作树可按需创建：

~~~powershell
python .\others\scripts\workflow.py worktree --role G
~~~

托管工作树工具从 main 创建任务分支；已有工作区会报告干净状态、HEAD 和相对基线的同步状态，存在不代表可开工。目录被其他内容占用时保留原状。A 发布后续基线后，子聊天先保留或提交未完成修改，再在干净的自己的分支执行 git merge 指定的基线SHA。不要重置工作区。

使用 `python .\others\scripts\workflow.py status --baseline a2-start` 查看角色登记、源码同步和各自契约版本；registered、clean、contains_baseline、ownership_current 均满足才 ready。后续使用 A 最新发布 SHA；省略参数时以当前 main 为准。任务提交从已提交的 main 核对所有权，拒绝错误路径和过期规则；`checkpoint --baseline 已发布SHA` 验证指定基线，省略时须包含当前 main。

## 每轮提交

先运行本轮相关真实检查并查看差异。然后在对应工作区执行，例如：

~~~powershell
python .\others\scripts\workflow.py checkpoint --role B --message "feat(core): add course enrollment" --check-note "course API tests: PASS" --paths others/backend/app/domains/core web/src/features/admin
~~~

路径必须属于该角色、本轮实际改动。工具拒绝错误分支、超出范围的路径以及夹带其他暂存文件；运行差异检查后提交。没有差异则不建空提交。

受外部条件阻塞时，使用 --wip，check-note 如实列出失败与未完成内容；WIP 不能当作可合并的完成状态。仅根目录准备检查可执行时，不声称已通过业务测试。

每轮提交后在本聊天记录角色、分支、commit ID、改动、检查和剩余问题；向A主的简报按统一协作规范合并到里程碑，不逐提交发送，普通简报不等回执。main正式接收与阶段放行仍由A主决定。

## A 合并

1. 检查子分支提交、测试证据及权限/契约影响。
2. 当前主工作区干净后，运行 git merge --no-ff 角色对应分支，名称以 ownership.json 为准。
3. 解决冲突并运行相关检查，记录合并提交。更新通用 Open-Web.cmd、Open-Windows.cmd、Open-Android.cmd、Open-A1.cmd 及共用启动器，保持旧入口可用。
4. 每轮功能集成新增对应入口，例如 Open-A2.cmd、Open-A3.cmd，复用共用启动逻辑，提供本轮角色/搜索/业务演示步骤。尚未集成的轮次不提前提供可用假入口。
5. 重新构建受影响的网页、Windows和安卓包；实际从入口启动，核对包内源码/契约版本及本轮功能，避免入口仍打开旧包。记录启动、失败、截图及产物版本。
6. 保留工作区和任务分支供后续使用；删除、强制重置和历史改写另行处理。

## 三个已授权的云端推送节点

远端固定为 origin：https://github.com/Qian-ff/refactored-couscous.git。用户已明确授权下列节点由 A 推送 main 和对应里程碑标签，不需再次询问。节点按集成轮次计算，不按逐个分支的 git merge 命令数量计算。

| 节点 | 触发条件 | 基线标签 |
|---|---|---|
| 第1次：当前交接 | 当前 A1 底座、一键工具及本轮角色/搜索要求提交并检查后立即推送 | checkpoint-1；同时保留并上传历史 a1-0.1.0 标签 |
| 第2次：A第二轮集成 | B/C/D 均完成约定交付，A 合并、联调并验证本轮一键入口后推送 | checkpoint-2 |
| 第3次：A第三轮集成 | 后续第三轮功能合并及相关验收完成后推送；预计包含C后续监控/A副原生等，具体范围按当轮任务 | checkpoint-3 |

每轮代码修改仍须本地提交；非上述节点不自行额外推送，A副及B/C/D/G仅提交自己的本地任务分支。每次推送记录完整提交 SHA，并用 ls-remote 核对远端 main/标签。推送失败不记作已上传；保留本地提交、准确报告原因，再在同一节点恢复，不改写远端历史。构建包、环境、账号密码、数据库与私密参考文件继续留在忽略区；这次授权是 Git 仓库备份，不含部署或公开发布安装包。

checkpoint-1 是已上传的历史交接；本轮 B/C/D 使用 a2-start 和 A 后续发布的完整 SHA，详见 a2-start.md。历史标签均不覆盖或重打。仅项目级 user.name/user.email 使用用户提供值，不修改全局配置。
