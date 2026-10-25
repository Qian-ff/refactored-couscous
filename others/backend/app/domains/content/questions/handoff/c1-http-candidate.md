# C1 HTTP候选与D/A接缝

本文件不是公共API发布记录。C只新增questions/routes.py、lessons/routes.py及其私有依赖/响应模型；没有修改main.py、公共契约、SDK、迁移或D入口。A副2须按生效委托实际挂载、集成并跑PG/HTTP，再由A发布技术SHA。路径假设沿用公共`/api/v1`前缀。

## 通用规则

两个router分别使用`/content/questions`、`/content/lessons`前缀。所有接口均为当前教师/管理员身份；依赖既有CurrentIdentity并追加staff检查，学生不能把purpose参数当作答案读取权。所有写请求要求8..128字符Idempotency-Key。分页offset>=0、limit=1..100，关键词最长100字符；领域SQL在计数/分页前授权，并逐条重验详情。

创建/修改/提审/决定/发布/复制/引用及导入导出分配额度时依赖`questions.http.C1Environment`。A在正式app.state.c1_environment注入真实ContentBudget与TransferAdmission；未配置环境返回503。默认空回调不代表可用，不能以单元测试的空配额/空准入回调运行产品。

## 教师/管理员接口

| 功能 | Questions | Lessons |
|---|---|---|
| 范围题库/关卡库 | GET /banks | GET /banks |
| 草稿列表/详情 | GET /drafts、/drafts/{question_id} | GET /drafts、/drafts/{lesson_id} |
| 创建/修改 | POST /drafts、PATCH /drafts/{question_id} | POST /drafts、PATCH /drafts/{lesson_id} |
| 放弃草稿 | POST /drafts/{question_id}/discard | POST /drafts/{lesson_id}/discard |
| 主记录停用/恢复 | PATCH /{question_id}/retirement | PATCH /{lesson_id}/retirement |
| 固定版本列表/详情 | GET /versions、/versions/{version_id} | GET /versions、/versions/{version_id} |
| 提审 | POST /drafts/{question_id}/submit | POST /drafts/{lesson_id}/submit |
| 审核记录列表/详情 | GET /reviews、/reviews/{review_id} | GET /reviews、/reviews/{review_id} |
| 审核/发布 | POST /reviews/{review_id}/decision、/publish | 同左 |
| 发布绑定列表/停用 | GET /publications、POST /publications/{publication_id}/retire | 同左 |
| 授权复制/引用 | POST /copies、/references | 同左 |
| 安全SVG创建 | 无 | POST /scenes |
| 固定教师预览 | 无 | GET /versions/{version_id}/preview |
| 受控SVG预览 | 无 | GET /versions/{version_id}/preview/scene、/drafts/{lesson_id}/scene |

版本列表支持parent ID、library_id及关键词；题目额外支持知识点。老师题目DTO含答案，仅在staff接口返回；TeacherLessonPreview与StudentLesson严格分开，预览不写正式学习记录。SVG仅经已授权关卡/草稿返回，不提供裸asset_id/hash或静态目录接口；响应private/no-store、nosniff、CSP sandbox/default-src none。

范围库的创建与调整仍复用既有C02公共library接口，不新建另一套组织管理接口。D使用正式生成SDK，不能从这些候选路由文字推定公共接口已存在。

## 交换任务接口候选

仅questions下：POST /imports；GET /imports/{batch_id}、/rows、/created；POST /imports/{batch_id}/confirm；POST /exports；GET /tasks/{task_id}；POST /tasks/{task_id}/cancel、/retry。响应分别为BatchView、Page[ImportRowView]、Page[CreatedQuestion]、TransferResult、TransferView。状态响应不返回私有文件key、执行/租约ID或题干答案。

实际上传字节及导出下载流尚未实现，未注册虚假成功入口。后续必须接真实封存/hash/长度、跨块撤权、stop-before-start/清理和共享计量；不得将私有export_worker_input或export_download存储票据注册成公开JSON接口。详情见c1-transfer-format.md。

## B2与学生

受控Python服务见questions/assessment.py、lessons/assessment.py；不能注册通用学生答案读取接口。本router不提供正式学生JSON或SVG。B2必须在实际任务、固定版本、当前课程/班级和解锁门禁下提供两者，发布时保留自己的评分/内容/素材快照；不得让普通R或asset_id绕过任务。

## 当前验证边界

隔离FastAPI应用的纯检查覆盖候选OpenAPI生成、幂等header、所有候选管理路由学生拒绝、未配置503和被动SVG响应头；测试明确覆盖CurrentIdentity/db依赖或领域服务，不是JWT、组织授权、真实SQL、迁移、进程、存储或公网API通过证据。未修改现行发布OpenAPI/SDK；A副2公共接入后须替换成真实身份与PG联合检查。
