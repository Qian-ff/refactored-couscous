# C-02 M1 模型/执行接口草稿（尚未交付）

当前模块不在公共models.py注册、不挂路由、不创建表。下一步仍须补服务、上传、审核、调度、测试及完整c-02-integration.md，不能把本草稿视为M1完成。

## 数据约束接入

八张表均在content/models.py：content_library、content_material、content_upload、content_material_version、content_source_chunk、content_material_review、content_material_publication、content_job。

- MaterialVersion使用upload_id真实FK，不以file_key授权；input_kind约束文件/文字互斥。
- Publication使用review/version/target三列复合FK避免串绑；approved状态仍需命令事务和数据库保护。
- Upload活跃会话按owner唯一；Job活跃尝试按version唯一。全局流数量、任务数量和配额仍需短事务及运行适配器共同执行，索引不代替这些规则。
- 组织复合FK目前约束同校，实际学院、目录和班级组合必须从真实父级推导并校验。不得要求Course.college_id=CourseCatalog.college_id。A迁移接入时还需固定归属、原始输入、成功快照及已决定审核不可覆盖的数据库保护；本轮尚未提供完整迁移说明/保护SQL。
- 上传/版本之间存在封存回指，A处理建表顺序与命名循环外键。首次创建上传时sealed_version_id为空，封存版本后才写回；所有删除保持NO ACTION/RESTRICT语义。
- 计量字段仅存预算，不证明实际已清理。清理确认后才可结算；不得仅因终态自动把预留清零。

## 解析适配器接口

content/parse_runner.py定义C/A候选接口。start接ParseTask及AsyncIterator[bytes]；C只传已授权不可变输入字节，不传任意宿主路径/命令。A复制到本任务专用只读输入，核对哈希和格式，使用固定模板启动。A须对输入总量也执行格式对应上限，失败清理后再释放排他执行。重复job_id/generation启动须幂等，失去响应先inspect，不盲目重启。

inspect/stop/result通过不透明execution_id定位。stop必须确认完整执行单元已结束，无法确认则不能启动替代任务。result读取过程中执行16MiB上限，不信任结果中的路径。能力声明只用于拒绝明显不满足的适配器，不是实际沙箱/隔离证据；A仍须实测网络、挂载、密钥、硬资源、取消和跨实例排他。

UnavailableRunner显式报PARSER_UNAVAILABLE，不尝试普通子进程降级，也不虚构停止成功。

## 当前检查范围

业务解释器下4项模型/SQL编译检查和2项runner能力检查通过，未连接数据库。查询使用真实B授权SQL及详情二次判权，多个发布绑定通过EXISTS避免版本重复。尚未进行真实PG权限/并发/快照保护验收，不能作业务完成证据。

新增服务候选见services.py、schemas.py、quota.py。配额计量不按终态过滤，未清理残留/保留快照继续占额；全局锁只包短事务，调用方须在事务外采集真实free_disk_bytes。当前缺容量探针返回503。尚需上传、调度和最终结算路径全部采用同一锁序并以PG竞争实测。

待审核版本的目标V必须能核对原件；readable_versions新增对应submitted/approved Review的目标V分支（B未发布资源R语义，creator为空），详情再次确认目标review能力。S和学生不能通过提审绑定获得草稿权限。输出投影只能带授权目标，不泄露源库字段；正式DTO/HTTP和PG隔离验收仍待补齐。
