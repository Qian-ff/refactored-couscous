# C1示范内容：60题、六关待审核草稿

全部内容为安研通原创情境表达、AI辅助起草，未获得专业教师批准。没有创建正式审核、发布、成绩或校园准入记录；公开/教学复用许可标记均为false，公开授权须项目组确认。参考站点提供概念核对，不代表这些站点编写、认可或提供本项目题库；外国法规与电话号码没有作为本校执行要求导入。

## 实际交付

- questions/seeds.py：60题的可审阅源数据。通识30、化学30；六主题各10，合计单选36、判断12、多选6、情境6。问题和选项ID不编码正确答案；题干/选项规范化去重通过。
- questions/seed-data/questions.json：含题目、答案、解析、作者/来源/许可状态和本包hash的后台私有草稿清单。
- questions/seed-data/general.csv、chemistry.csv：分别30题，经过真实CSV编解码回导验证。该教师资料含私有答案，不作为学生静态资源。
- lessons/seeds.py、seed-data/lessons.json：两个班各三关：入室防护/设备用电/应急处置，试剂标签储存/操作通风/废物泄漏。每关有独立短课、选择/定位/排序三类活动及私有评分。
- lessons/seed-data/*.svg：六份原创蓝绿二维俯视教学示意，通过既有被动SVG校验并各有独立hash，不使用外部图片/图标。图中不是校园真实平面图；文字替代描述与区域坐标同时提供。尚未做正式三端渲染/用户体验验收。

JSON/SVG清单是草稿资产，不是已入库LessonVersion。lesson_seed(topic, actual_asset_uuid)在实际插入SceneAsset后才构造正式校验模型，不伪造版本或把种子UUID冒充数据库记录。关卡互动为独立原创活动，不用材料指针伪装题目版本引用；后续教师若选用实际题库题目，仍须严格绑定question_version_id。

## 来源与授权记录

2026-10-25核对了下列公开页面的相关概念，没有保存/转载网页全文、图片或官方原题：

- [Princeton EHS：一般实验工作要求](https://ehs.princeton.edu/laboratory-research/laboratory-safety/laboratory-safety-manual/sec7)、[个体防护](https://ehs.princeton.edu/laboratory-research/laboratory-safety/ppe-the-lab)。
- [Princeton EHS：电气安全](https://ehs.princeton.edu/laboratory-research/laboratory-safety/laboratory-safety-manual/sec7g)、[日常检查与整改](https://ehs.princeton.edu/take-10-and-take-action)。
- [Princeton EHS：应急预案与报告](https://ehs.princeton.edu/laboratory-research/laboratory-safety/laboratory-safety-manual/sec3)。
- [OSHA：实验室化学危害标准](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450)、[HSE：安全数据表](https://www.hse.gov.uk/coshh/basics/datasheets.htm)。
- [Princeton EHS：化学通风柜](https://ehs.princeton.edu/laboratory-research/laboratory-safety/laboratory-equipment-and-engineering/fume-hoods)、[实验室通风](https://ehs.princeton.edu/laboratory-research/laboratory-safety/laboratory-safety-manual/sec6b)、[化学废物管理](https://ehs.princeton.edu/laboratory-research/chemical-waste-management)。

外部页面缺少稳定版本或未保留原始字节时，publisher_version/publisher_content_hash明确为null；不能用本包hash冒充外部原文hash。HSE页面显示OGL v3.0，其余来源未确认开放再分发许可，均只保留链接。题目与场景的本包内容hash可确定性再生成；出处、获取日期、原创改编说明和许可状态在questions.json记录。使用前应由本校教师逐条核对本地规程、术语、适用范围与解析。

## 导入与再生成

`lessons/seeding.import_demo_drafts`为内部候选服务，只接两个已有、同校且不同教学班的课程库；验证当前S权限后原子写入60个QuestionDraft、六个SceneAsset及六个LessonDraft。缺少公共统一配额会回滚；幂等重放不重复导入；重复题按现有规则拒绝，不覆盖已有内容。不自动创建学校/课程/账号，也不提审或发布。尚未在真实PG运行；PG候选见lessons/tests/pg/test_seeding.py。

开发者可在本C树再生成静态资产：

```powershell
python .\others\scripts\shared_env.py backend app.domains.content.questions.seed_export
```

该命令只写C1两个模块内固定seed-data目录，不读取私密PPT、不联网调用AI、不安装依赖或访问数据库。环境与锁须仍匹配A已激活基线；A正在切换共享依赖时不要重建环境。

## 本轮验证与接棒

4项纯检查通过：60题数量/分组/四题型/去重/草稿许可、全部CSV真实往返、六份不同SVG与LessonContent/StudentLesson投影、manifest确定性与外部版本/hash不虚构。Ruff通过。证明输入模型和静态内容可被处理，不证明教学专业正确性、PG入库、三端显示或正式学习解锁。

A同步的main 29d0d7f92698cb62fc25f1247ecaed21eae8d481已接C02后台源码0.4.0，但运行激活仍待A副，C没有自行合并或改共享依赖。后续按其coordination的当前演示检查范围：正常业务、授权/租户、数据/版本和必要小型输入检查，不追加攻击/耗尽/完整压力矩阵；保留既有保护与历史证据。
