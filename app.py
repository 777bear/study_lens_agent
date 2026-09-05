from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from studylens.agent import StudyLensAgent
from studylens.demo import demo_result
from studylens.export import render_study_html
from studylens.llm import ModelConfig


ROOT = Path(__file__).parent

st.set_page_config(
    page_title="课析 StudyLens",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(f"<style>{(ROOT / 'assets' / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def model_config() -> ModelConfig:
    return ModelConfig(
        api_key=st.session_state.get("api_key", ""),
        base_url=st.session_state.get("base_url", "https://api.openai.com/v1"),
        reasoning_model=st.session_state.get("reasoning_model", "gpt-4.1-mini"),
        vision_model=st.session_state.get("vision_model", "gpt-4.1-mini"),
        temperature=0.2,
    )


def run_analysis(uploaded_file) -> None:
    suffix = Path(uploaded_file.name).suffix.lower()
    temp_root = Path(tempfile.mkdtemp(prefix="studylens-"))
    source = temp_root / f"course{suffix}"
    source.write_bytes(uploaded_file.getvalue())
    agent = StudyLensAgent(model_config())
    progress_bar = st.progress(0.0, text="准备分析…")

    def update(value: float, message: str) -> None:
        progress_bar.progress(min(max(value, 0.0), 1.0), text=message)

    try:
        result = agent.analyze(source, temp_root / "analysis", progress=update)
    except Exception as exc:
        progress_bar.empty()
        st.error(f"分析没有完成：{exc}")
        return
    st.session_state.result = result
    st.session_state.chat_history = []
    st.session_state.last_config = model_config()
    progress_bar.empty()
    st.success(f"已将 {len(result.slides)} 页课件重构为复习讲义。")


with st.sidebar:
    st.markdown('<div class="side-brand">◉ 课析 <span>StudyLens</span></div>', unsafe_allow_html=True)
    st.caption("把杂乱课件，变成真正能学会的复习系统")
    st.markdown("---")
    uploaded = st.file_uploader("上传教师课件", type=["pptx", "pdf"], help="支持 PPTX、PDF，建议单文件不超过 80 MB")
    analyze_clicked = st.button("开始深度解析", type="primary", use_container_width=True, disabled=uploaded is None)
    demo_clicked = st.button("先看完整演示", use_container_width=True)
    with st.expander("模型服务", expanded=False):
        st.caption("可接云端 API，也可接本地 Qwen / Ollama 等兼容服务。密钥只保留在当前会话。")
        st.text_input("服务地址", value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), key="base_url")
        st.text_input("API 密钥", value=os.getenv("OPENAI_API_KEY", ""), type="password", key="api_key")
        st.text_input("推理模型", value=os.getenv("REASONING_MODEL", "gpt-4.1-mini"), key="reasoning_model")
        st.text_input("视觉模型", value=os.getenv("VISION_MODEL", "gpt-4.1-mini"), key="vision_model")
        if not model_config().enabled:
            st.info("未配置模型时仍可做本地文本解析和证据检索。")
    st.markdown("---")
    st.caption("隐私：上传文件保存在本次运行的临时目录，不写入公共知识库。")

if demo_clicked:
    st.session_state.result = demo_result()
    st.session_state.chat_history = []
    st.session_state.last_config = model_config()

if analyze_clicked and uploaded is not None:
    run_analysis(uploaded)

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">PPT → KNOWLEDGE → MASTERY</div>
      <h1>不是摘要课件，<br><em>而是重建学习路径。</em></h1>
      <p>逐页理解图文与公式，补齐必要背景，重排知识逻辑；每个关键结论保留页码证据，还能继续追问与自测。</p>
    </section>
    """,
    unsafe_allow_html=True,
)

result = st.session_state.get("result")
if result is None:
    st.markdown("<div class='section-label'>工作方式</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    steps = [
        ("01", "看懂每一页", "文字、表格、公式、图表和讲者备注交叉核验。"),
        ("02", "补齐理解门槛", "只补必要背景，并与课件原文明确区分。"),
        ("03", "重构完整讲义", "按知识依赖重排，而不是沿用混乱页序。"),
        ("04", "答疑与自测", "引用原页回答，并生成分层复习题和答案。"),
    ]
    for column, (number, title, body) in zip(cols, steps):
        with column:
            st.markdown(
                f"<article class='step-card'><span>{number}</span><h3>{title}</h3><p>{body}</p></article>",
                unsafe_allow_html=True,
            )
    st.markdown(
        "<div class='empty-note'>从左侧上传 PPTX / PDF，或点击“先看完整演示”体验最终效果。</div>",
        unsafe_allow_html=True,
    )
    st.stop()

pack = result.study_pack
st.markdown("<div class='result-head'>", unsafe_allow_html=True)
title_col, export_col = st.columns([4, 1])
with title_col:
    st.markdown(f"<div class='section-label'>复习空间 · {pack.source_pages} 页证据</div>", unsafe_allow_html=True)
    st.title(pack.course_title)
    st.markdown(f"<p class='result-summary'>{pack.one_sentence_summary}</p>", unsafe_allow_html=True)
with export_col:
    html_report = render_study_html(pack)
    st.download_button(
        "下载复习网页",
        data=html_report.encode("utf-8"),
        file_name="课析_复习讲义.html",
        mime="text/html",
        use_container_width=True,
    )
    st.caption("打开网页后可直接打印为 PDF")
st.markdown("</div>", unsafe_allow_html=True)

tab_map, tab_notes, tab_chat, tab_quiz, tab_sources = st.tabs(
    ["学习地图", "完整解析", "随问随答", "复习题", "原页证据"]
)

with tab_map:
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("### 学习概览")
        st.markdown(pack.overview)
        st.markdown("### 必要背景知识")
        st.markdown(pack.background_knowledge)
    with right:
        st.markdown("### 知识地图")
        st.markdown(pack.knowledge_map)
        st.markdown("### 复习计划")
        st.markdown(pack.review_plan)

with tab_notes:
    st.markdown('<div class="reading-sheet">', unsafe_allow_html=True)
    st.markdown(pack.detailed_notes)
    st.markdown("---")
    st.markdown("## 重点、难点与掌握标准")
    st.markdown(pack.key_points)
    st.markdown("## 易错点与核对提醒")
    st.markdown(pack.common_pitfalls)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_chat:
    st.markdown("### 对课件继续提问")
    st.caption("回答会优先检索原课件并附页码；课件没有的内容会标明为背景补充。")
    history = st.session_state.setdefault("chat_history", [])
    if not history:
        st.markdown(
            "<div class='question-chips'>可以试试：‘这章最容易混淆的两个概念是什么？’　‘第 3 页公式中的每个符号代表什么？’　‘给我一道应用题。’</div>",
            unsafe_allow_html=True,
        )
    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("输入你没看懂的地方…")
    if question:
        history.append({"role": "user", "content": question})
        cfg = st.session_state.get("last_config", model_config())
        agent = StudyLensAgent(cfg)
        with st.spinner("正在查找相关页并组织答案…"):
            try:
                answer, _chunks = agent.answer(question, result, history[:-1])
            except Exception as exc:
                answer = f"这次回答没有完成：{exc}"
        history.append({"role": "assistant", "content": answer})
        st.rerun()

with tab_quiz:
    st.markdown("### 分层复习题")
    st.caption("先独立作答，再展开答案。页码可回到“原页证据”核对。")
    if not pack.quiz:
        st.info("当前没有生成复习题。")
    for index, item in enumerate(pack.quiz, start=1):
        st.markdown(
            f"<div class='quiz-label'>{item.question_type} · {item.difficulty} · Q{index:02d}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {item.question}")
        for option in item.options:
            st.markdown(f"- {option}")
        with st.expander("查看答案与解析"):
            st.markdown(f"**答案：** {item.answer}")
            st.markdown(item.explanation)
            if item.citations:
                st.caption("证据：" + " · ".join(item.citations))
        st.markdown("---")

with tab_sources:
    st.markdown("### 原页证据")
    st.caption("这里展示 Agent 实际读取的页面信息，便于发现遗漏或核对模型解释。")
    for slide in result.slides:
        with st.expander(f"第 {slide.number} 页 · {slide.title or '未命名页面'}"):
            if slide.rendered_image and Path(slide.rendered_image).exists():
                image_col, text_col = st.columns([1, 1])
                with image_col:
                    st.image(slide.rendered_image, use_container_width=True)
                with text_col:
                    st.text(slide.evidence_text() or "本页没有可提取文字，请以页面图像为准。")
            else:
                st.text(slide.evidence_text() or "本页没有可提取文字。")

