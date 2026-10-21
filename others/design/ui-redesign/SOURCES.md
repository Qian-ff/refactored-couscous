# 素材与工具来源

版本：UI-2026.10-v1。所有人名、学校、账号、编码和日期为合成示例，无真实业务数据。

| 内容 | 来源 | 使用与许可 |
| --- | --- | --- |
| 中文字体 | Google Fonts / Noto Sans SC，固定提交 a85815a42757630ce188fdad368c2dfc444d4773 | 未修改原字体，SIL OFL 1.1，原许可随 assets/fonts/OFL.txt 保留；文件哈希见 source.json |
| 实验台、器皿、护目镜、电气装置与手套插图 | 本轮在 prototype.js 中用 SVG 原创绘制 | 作为本项目设计来源，未使用外部图片或模型 |
| 线性图标 | 本轮在 prototype.js 的 paths 中原创绘制 | 与静态源码一并交付；不是复制外部图标包 |
| 品牌与宣传语 | 用户确认的安研通 / LabConnect 名称与文案 | 不使用外部参考PPT的名称、图形或标识 |
| 页面信息与业务语义 | b1-ready 基线中的 App.tsx、admin、teaching 组件和契约0.3.1 | 只阅读已有实现，不引入真实业务数据 |
| 图片导出 | 项目已有 Playwright、本机 Microsoft Edge | 只复用已安装工具，不安装或修改依赖；不是产品构建 |

字体原始文件和许可的固定来源：

- [Noto Sans SC 字体](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf)
- [字体原许可](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt)

本目录不包含私密参考PPT、API密钥、真实账号、监控资料、虚拟环境或第三方产品截图。字体保留完整原文件用于离线审阅；正式前端是否子集化与最终包大小由 D/F 在实施时评估，不在图片阶段擅改共享依赖。

原创插图现已由extract-assets.cjs从已批准的prototype.js导出到assets/illustrations/（4个SVG），图标导出为assets/icons.svg；这些是同版SVG代码的独立文件，不是新来源或外部图片。移动稿沿用同一字体、图形与合成内容，来源和许可不变。
