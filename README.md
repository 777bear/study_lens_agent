# 课析 StudyLens Agent

把顺序混乱、图文混杂的教师 PPT/PDF 重构为一套真正适合学生复习的网页学习空间：完整讲义、必要背景、页码证据、连续答疑，以及带答案的分层复习题。

## 已实现

- PPTX/PDF 上传与按页解析；保留正文、讲者备注、表格、图表、内嵌图片和页码。
- 有 LibreOffice 时自动渲染整页，由视觉模型理解公式、流程图、截图和版式关系。
- 两阶段 Agent：先做逐页多模态分析，再做全局知识重构，避免只生成流水账摘要。
- 关键结论使用 `[第N页]` 引用；必要背景与课件原文明确区分。
- 中文页级证据检索与多轮答疑；无向量数据库也能本地运行。
- 学习地图、完整解析、易错点、复习计划、分层题库与答案。
- 一键下载独立 HTML，浏览器中可直接“打印 / 导出 PDF”。
- 云端与本地模型可替换：支持 OpenAI Chat Completions 兼容服务。
- 对课件中的提示词注入做数据/指令隔离，不把 PPT 文字当系统命令。

## 快速运行

需要 Python 3.10 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

打开页面后，可先点击“先看完整演示”。不配置模型时，上传课件仍可进行本地结构化解析和证据问答；配置视觉/推理模型后启用完整深度讲义。

## 模型配置

在页面左侧展开“模型服务”，填写服务地址、API 密钥、推理模型和视觉模型。也可使用环境变量：

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export REASONING_MODEL="gpt-4.1-mini"
export VISION_MODEL="gpt-4.1-mini"
```

接本地服务时，将 `OPENAI_BASE_URL` 改为本地兼容地址，例如 `http://127.0.0.1:11434/v1`，模型名称改为本地实际模型。视觉模型必须支持图片输入；如果整页渲染环境不可用，Agent 会退回结构化文本分析。

## Docker

```bash
docker build -t studylens .
docker run --rm -p 8501:8501 -e OPENAI_API_KEY="your-key" studylens
```

镜像安装 LibreOffice、Poppler 与 Noto CJK 字体，用于稳定渲染 PPT/PDF 页面。

## 处理流程

```text
课件上传
  → 结构化抽取 + 整页渲染
  → 每 4 页一批的多模态理解
  → 必要背景补全与全局知识重构
  → 复习网页 / PDF
  → 页级检索支撑的连续答疑与复习题
```

核心提示词在 `studylens/prompts.py`，流程编排在 `studylens/agent.py`，界面在 `app.py`。GitHub 基线调研与许可证说明见 `docs/github-research.md`。

## 测试

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

当前测试覆盖 PPT 结构与表格提取、中文证据检索及页码引用、网页导出和答案展示。

## 当前边界

- 旧版 `.ppt` 需先另存为 `.pptx`。
- 极长课件会增加模型调用耗时和成本；默认每批 4 页以平衡效果与稳定性。
- AI 解释可能出错，界面保留“原页证据”供学生核对；正式课程仍以教师与教材为准。
- 生产部署应增加用户鉴权、任务队列、文件自动清理和调用额度控制。

## 开源说明

项目代码使用 MIT License。实现借鉴了 MarkItDown、pptx-parser、WeKnora 和 Exameow 的公开思路，但未直接复制其源码；详见调研文档。

