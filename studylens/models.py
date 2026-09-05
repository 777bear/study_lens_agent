from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SlideContent:
    number: int
    title: str = ""
    text: str = ""
    notes: str = ""
    tables: list[str] = field(default_factory=list)
    charts: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    rendered_image: str | None = None

    @property
    def source_label(self) -> str:
        return f"第{self.number}页"

    def evidence_text(self) -> str:
        blocks = [self.title, self.text, self.notes, *self.tables, *self.charts]
        return "\n".join(block.strip() for block in blocks if block and block.strip())

    def to_prompt_dict(self, include_paths: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "page": self.number,
            "title": self.title,
            "text": self.text,
            "speaker_notes": self.notes,
            "tables": self.tables,
            "charts": self.charts,
        }
        if include_paths:
            data["rendered_image"] = self.rendered_image
        return data


@dataclass
class SourceChunk:
    page: int
    title: str
    content: str
    kind: str = "slide"
    score: float = 0.0

    @property
    def citation(self) -> str:
        return f"[第{self.page}页]"


@dataclass
class QuizItem:
    question_type: str
    difficulty: str
    question: str
    options: list[str] = field(default_factory=list)
    answer: str = ""
    explanation: str = ""
    citations: list[str] = field(default_factory=list)


@dataclass
class StudyPack:
    course_title: str
    one_sentence_summary: str
    overview: str
    background_knowledge: str
    knowledge_map: str
    detailed_notes: str
    key_points: str
    common_pitfalls: str
    review_plan: str
    quiz: list[QuizItem] = field(default_factory=list)
    source_pages: int = 0
    generated_by: str = "local-fallback"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StudyPack":
        quiz = [item if isinstance(item, QuizItem) else QuizItem(**item) for item in payload.get("quiz", [])]
        fields = {
            "course_title": payload.get("course_title", "未命名课件"),
            "one_sentence_summary": payload.get("one_sentence_summary", ""),
            "overview": payload.get("overview", ""),
            "background_knowledge": payload.get("background_knowledge", ""),
            "knowledge_map": payload.get("knowledge_map", ""),
            "detailed_notes": payload.get("detailed_notes", ""),
            "key_points": payload.get("key_points", ""),
            "common_pitfalls": payload.get("common_pitfalls", ""),
            "review_plan": payload.get("review_plan", ""),
            "quiz": quiz,
            "source_pages": int(payload.get("source_pages", 0) or 0),
            "generated_by": payload.get("generated_by", "llm"),
        }
        return cls(**fields)


@dataclass
class AnalysisResult:
    slides: list[SlideContent]
    study_pack: StudyPack
    slide_analyses: list[dict[str, Any]] = field(default_factory=list)
    workspace: Path | None = None

