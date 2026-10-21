# 安研通公共界面：D-UI 第一批

基于 UI-2026.10-v1 和悬浮助手 v1.1 冻结规范。实施使用 frontend-design，目标为原 D 分支的组件交接，完整 B 展示迁移、D 二次整合和原生验收仍由后续阶段完成。

## 布局方案与自查

颜色：青 #087F8C、辅助蓝 #2563EB、工作底 #F5F8FA、纸面 #FFFFFF、正文 #172B3A、结构线 #DCE7EB。
字体：包内原始 Noto Sans SC 可变字体，LabNoto 别名；正文15px，桌面标题32px，手机26px，控制命中至少44px。

桌面为208px记录簿侧栏、80px身份栏、单一工作区；手机为顶部菜单及导航抽屉，学生另保留批准的未开放功能位置。
登录采用实验器材主视觉与右侧表单；手机收起大插图。注册分“核验邀请→填写资料→手动登录”；本人资料为只读身份清单与可编辑联系方式。

自查后采用真实课程总数与授权教学班，不增加虚构统计。业务页保持连续表单/列表，实验器材体积只用于账号与学生课程区。图稿仅提供风格，真实接口、幂等、revision及会话规则始终保留。

## B 可消费的导出

统一从 `web/src/components/labconnect/index.tsx` 导入：

| 导出 | 核心属性与行为 |
|---|---|
| Button | 原生button属性；variant=primary/secondary/quiet/danger；pending时禁用并播报忙状态，默认type=button |
| Field | label、hint、error、children；使用真实input/select/textarea，不用div模拟控件 |
| Notice | kind=info/error/success/warning、children、retry；错误使用alert，其余status |
| StatePanel | loading/empty/error/offline/forbidden/unconfigured/unavailable；title、description、retry |
| PageContainer | title、description、actions、children；提供唯一main与h1，无外层工作区padding |
| Panel | title、actions、children；提供区域边框、标题和内部24px/手机20px内距 |
| SearchFilters | value、onChange、onSearch、onClear、label、placeholder、pending、children；中文IME期间不提交 |
| Pagination | total、offset、pageSize、onChange、pending；服务端总数，不对当前页自行计算总数 |
| RecordList<T> | items、itemKey、title、fields(label/value)、actions；标签化字段与移动重排 |
| Dialog | title、onClose、busy、long、children；原生modal焦点圈定，Escape/关闭与焦点恢复；busy时阻止关闭 |

示例：

```tsx
import { PageContainer, Panel, Button, Pagination } from "../../components/labconnect"
return <PageContainer title="课程与教学班" description="按当前授权范围管理。"
  actions={<Button onClick={openCreate}>新建课程与首班</Button>}>
  <Panel title="有权访问的教学班">{existingRecords}</Panel>
  <Pagination total={response.count} offset={offset} pageSize={20} onChange={setOffset} />
</PageContainer>
```

壳负责且仅负责一次工作区38px/手机16px间距及最大宽度；PageContainer负责main和页标题，B不要再包main或添加整页padding/max-width。现有B仍保留BusinessPage.main，D仅在边界类lc-business-slot去掉其外层重复间距。B迁移后移除旧BusinessPage的main/页标题，直接使用PageContainer；Section迁到Panel但保留自身业务标题。壳的顶栏是当前位置，不重复生成整页标题。

B的现有ui.tsx/business.css/业务hooks完全未改；B保留其SessionPage、请求代次、查询取消、幂等键及revision规则。公共hooks.ts供D使用，不要求B替换已验证的业务钩子。页面继续导出PageRegistration，基础组件不反向导入B。

## 资源与分发

assets/fonts的原字体、OFL及source.json与冻结设计逐字节一致；assets/illustrations和icons.svg为同版原创图形副本。运行时不从others/design导入。字体许可通过正式入口引用为构建资源，随web/dist分发；A另补others/licenses归档供统一许可清单。字体未子集化，原文件约17.8MB，首屏使用font-display:swap。

## 验证与公共协调

本批检查、运行版本和截图位置见D交接记录；不把浏览器390px检查称为Windows/安卓原生验收。

交A：更新旧任务书“注册助手页”残余文字，保持未来唯一悬浮宿主；C开工前明确云API与本地ASR worker部署、鉴权及连接方式。公共旧测试的选择器应随真实入口更新，不移除原有业务断言。
