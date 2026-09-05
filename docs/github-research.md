# GitHub 开源基线调研

本项目先调研开源实现，再选择适合校内竞赛现场演示的轻量方案。未直接复制第三方源码；实现吸收了其公开架构思路，并在产品定位、提示词、学习内容结构和交互上重新设计。

| 项目 | 可借鉴能力 | 本项目的采用方式 | 许可证 |
|---|---|---|---|
| [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | PPTX/PDF 转 Markdown、图像描述与 OCR 插件 | 保留“结构化文本 + 视觉描述互补”的双通道思想；本项目额外保留稳定页码证据 | MIT |
| [vavlani/pptx-parser](https://github.com/vavlani/pptx-parser) | PPTX/PDF 文本抽取、整页渲染、逐页 AI 描述 | 采用“每页文本 + 整页图像”的分析单元，并增加批处理和全局课程重构 | MIT |
| [Tencent WeKnora](https://github.com/Tencent/WeKnora) | 文档知识库、RAG 问答、Agent 推理 | 借鉴检索后回答与证据约束；为课堂场景缩减为无需数据库的中文页级检索 | MIT |
| [Exameow](https://github.com/heshengtao/exameow) | 多格式学习材料、分题型题库、本地优先 | 借鉴分层题型与本地优先；新增“必要背景—完整讲义—页码证据—追问”的闭环 | Apache-2.0 |

## 本项目的差异化

1. 目标不是把 PPT 变成另一份摘要，而是恢复知识依赖关系并重建复习路径。
2. 每个关键解释尽量带页码，课件原文、背景补充和合理推断三者分开。
3. 问答使用同一份页级证据，不让聊天脱离教师课件自由发挥。
4. 输出是适合阅读、打印和导出 PDF 的完整网页讲义，并附复习题答案。
5. 模型层可替换，可接云端 API 或校内部署的 Qwen/Ollama 兼容服务。

