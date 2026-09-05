from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .llm import CompatibleLLM, LLMError, ModelConfig, parse_json_object
from .models import AnalysisResult, QuizItem, SlideContent, StudyPack
from .parser import PresentationParser
from .prompts import (
    QA_SYSTEM,
    QA_TEMPLATE,
    SLIDE_ANALYSIS_SYSTEM,
    SLIDE_BATCH_TEMPLATE,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_TEMPLATE,
)
from .retrieval import EvidenceRetriever


ProgressCallback = Callable[[float, str], None]


class StudyLensAgent:
    def __init__(self, model_config: ModelConfig | None = None):
        self.model_config = model_config or ModelConfig()
        self.llm = CompatibleLLM(self.model_config)
        self.parser = PresentationParser()

    def analyze(
        self,
        source: str | Path,
        workspace: str | Path,
        progress: ProgressCallback | None = None,
    ) -> AnalysisResult:
        notify = progress or (lambda _value, _message: None)
        notify(0.03, "正在安全读取课件结构…")
        slides = self.parser.parse(source, workspace)
        if not slides:
            raise RuntimeError("课件中没有可分析的页面。")
        notify(0.14, f"已读取 {len(slides)} 页，正在恢复逐页含义…")

        if not self.model_config.enabled:
            pack = self._fallback_pack(slides)
            notify(1.0, "已完成本地基础解析；接入模型后可生成深度讲义。")
            return AnalysisResult(slides=slides, study_pack=pack, workspace=Path(workspace))

        slide_analyses: list[dict] = []
        batch_size = 4
        for start in range(0, len(slides), batch_size):
            batch = slides[start : start + batch_size]
            prompt_slides = [slide.to_prompt_dict() for slide in batch]
            images = [
                (slide.source_label, slide.rendered_image)
                for slide in batch
                if slide.rendered_image and Path(slide.rendered_image).exists()
            ]
            prompt = SLIDE_BATCH_TEMPLATE.format(
                slides_json=json.dumps(prompt_slides, ensure_ascii=False, indent=2)
            )
            raw = self.llm.complete(
                SLIDE_ANALYSIS_SYSTEM,
                prompt,
                model=self.model_config.vision_model if images else self.model_config.reasoning_model,
                images=images,
                json_mode=True,
                max_tokens=6_000,
            )
            payload = parse_json_object(raw)
            slide_analyses.extend(payload.get("slides", []))
            value = 0.14 + 0.56 * min(1.0, (start + len(batch)) / len(slides))
            notify(value, f"已理解第 {start + 1}–{start + len(batch)} 页…")

        notify(0.74, "正在补齐必要背景并重构复习逻辑…")
        compact = json.dumps(slide_analyses, ensure_ascii=False, indent=2)
        if len(compact) > 110_000:
            compact = compact[:110_000] + "\n[内容过长，后续页已截断，请结合原页检索补充]"
        synthesis_prompt = SYNTHESIS_TEMPLATE.format(
            page_count=len(slides),
            slide_analyses=compact,
        )
        raw_pack = self.llm.complete(
            SYNTHESIS_SYSTEM,
            synthesis_prompt,
            model=self.model_config.reasoning_model,
            json_mode=True,
            max_tokens=15_000,
        )
        pack_payload = parse_json_object(raw_pack)
        pack_payload["source_pages"] = len(slides)
        pack_payload["generated_by"] = self.model_config.reasoning_model
        pack = StudyPack.from_dict(pack_payload)
        notify(1.0, "复习讲义、重点难点和题库已生成。")
        return AnalysisResult(
            slides=slides,
            study_pack=pack,
            slide_analyses=slide_analyses,
            workspace=Path(workspace),
        )

    def answer(
        self,
        question: str,
        result: AnalysisResult,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list]:
        retriever = EvidenceRetriever(result.slides)
        chunks = retriever.search(question, top_k=5)
        context = retriever.format_context(chunks)
        if not chunks:
            return "课件中没有检索到足够相关的内容。可以换一个更具体的关键词，或指出页码后再问。", []
        if not self.model_config.enabled:
            evidence = "\n\n".join(
                f"**{chunk.citation} {chunk.title}**\n\n{chunk.content[:900]}" for chunk in chunks[:3]
            )
            answer = (
                "当前为本地基础模式，先给出最相关的课件原文证据：\n\n"
                f"{evidence}\n\n"
                "如需因果解释、背景补充和追问式答疑，请在侧栏配置模型服务。"
            )
            return answer, chunks
        compact_history = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')[:800]}" for item in (history or [])[-6:]
        )
        prompt = QA_TEMPLATE.format(
            question=question,
            context=context,
            history=compact_history or "无",
        )
        answer = self.llm.complete(
            QA_SYSTEM,
            prompt,
            model=self.model_config.reasoning_model,
            max_tokens=3_500,
        )
        return answer, chunks

    @staticmethod
    def _fallback_pack(slides: list[SlideContent]) -> StudyPack:
        title = next((slide.title for slide in slides if slide.title.strip()), "未命名课件")
        note_sections: list[str] = []
        key_lines: list[str] = []
        quiz: list[QuizItem] = []
        for slide in slides:
            evidence = slide.evidence_text().strip()
            if not evidence:
                continue
            heading = slide.title or f"第{slide.number}页"
            note_sections.append(f"### {heading} [第{slide.number}页]\n\n{evidence}")
            key_lines.append(f"- **{heading}**：复习本页定义、条件和例子。[第{slide.number}页]")
            if len(quiz) < 8:
                quiz.append(
                    QuizItem(
                        question_type="简答",
                        difficulty="基础",
                        question=f"请用自己的话概括“{heading}”这一页的核心内容。",
                        answer=evidence[:500],
                        explanation="答案应覆盖本页主旨，并能说明关键词之间的关系。",
                        citations=[f"第{slide.number}页"],
                    )
                )
        return StudyPack(
            course_title=title,
            one_sentence_summary="已完成课件文本、表格与图表信息的本地结构化整理。",
            overview=(
                f"本课件共 {len(slides)} 页。当前未连接大模型，以下内容为可核对的本地基础解析。"
                "配置侧栏模型后，Agent 会补全背景、解释公式图表、重组学习路线并生成分层题库。"
            ),
            background_knowledge="> 当前为本地基础模式，未自动补充课件之外的背景知识，以避免无模型时编造内容。",
            knowledge_map="\n".join(key_lines) or "暂无可提取标题。",
            detailed_notes="\n\n".join(note_sections) or "课件页面没有可提取文字，请使用支持视觉的模型重新分析。",
            key_points="\n".join(key_lines) or "暂无。",
            common_pitfalls="- 文本抽取可能遗漏公式、流程图和截图信息；请对照“原页证据”标签核验。",
            review_plan=(
                "1. 先浏览知识地图并圈出陌生术语。\n"
                "2. 按页阅读基础解析，对照原 PPT。\n"
                "3. 完成复习题；不能复述的页重新学习。"
            ),
            quiz=quiz,
            source_pages=len(slides),
            generated_by="local-fallback",
        )

