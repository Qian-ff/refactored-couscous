# Git 与多聊天工作区

用户要求：每轮代码生成或修改结束保存本地提交，分支聊天提交自己的分支。仓库规则由根 AGENTS.md 生效；此文给出操作步骤。

## 分支与工作区

A 使用主目录 main；B–G 由 ownership.json 指定 task 分支，使用忽略的 others/worktrees 下独立副本。工作区之间共享 Git 历史，不共享可写源码。最多同时运行四个聊天。

初始化后的创建命令：

~~~powershell
python .\others\scripts\workflow.py worktree --role B
python .\others\scripts\workflow.py worktree --role C
python .\others\scripts\workflow.py worktree --role D
python .\others\scripts\workflow.py worktree --role E
python .\others\scripts\workflow.py worktree --role F
python .\others\scripts\workflow.py worktree --role G
~~~

工具从 main 创建任务分支；已有工作区会报告干净状态、HEAD 和相对基线的同步状态，存在不代表可开工。目录被其他内容占用时保留原状。A 发布基线后，子聊天先保留或提交未完成修改，再在干净的自己的分支执行 git merge 指定的基线SHA。不要重置工作区。

使用 `python .\others\scripts\workflow.py status --baseline 已发布SHA` 查看所有工作区是否包含基线及各自契约版本；省略参数时以当前 main 为准。任务提交检查从已提交的 main 核对所有权，拒绝本分支的过期规则；`checkpoint --baseline 已发布SHA` 验证分支包含指定基线，省略时须包含当前 main。

## 每轮提交

先运行本轮相关真实检查并查看差异。然后在对应工作区执行，例如：

~~~powershell
python .\others\scripts\workflow.py checkpoint --role B --message "feat(core): add course enrollment" --check-note "course API tests: PASS" --paths others/backend/app/domains/core web/src/features/admin
~~~

路径必须属于该角色、本轮实际改动。工具拒绝错误分支、超出范围的路径以及夹带其他暂存文件；运行差异检查后提交。没有差异则不建空提交。

受外部条件阻塞时，使用 --wip，check-note 如实列出失败与未完成内容；WIP 不能当作可合并的完成状态。仅根目录准备检查可执行时，不声称已通过业务测试。

提交后交付：角色、分支、commit ID、改动、检查、剩余问题。

## A 合并

1. 检查子分支提交、测试证据及权限/契约影响。
2. 当前主工作区干净后，运行 git merge --no-ff task/对应分支。
3. 解决冲突并运行相关检查，记录合并提交。
4. 保留工作区和任务分支供后续使用；删除、强制重置和历史改写另行处理。

本地 commit 不等于 GitHub 上传。远端 origin 已由用户指定；push 按用户后续明确指令执行。仅项目级 user.name/user.email 使用用户提供值，不修改全局配置。
