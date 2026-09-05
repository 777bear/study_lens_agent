from __future__ import annotations

import math
import re
from collections import Counter

from .models import SlideContent, SourceChunk


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _features(text: str) -> Counter[str]:
    """适配中英文的轻量检索特征：中文字符二元组 + 英文/数字词元。"""
    normalized = _normalize(text)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    grams = [chinese[i : i + 2] for i in range(max(0, len(chinese) - 1))]
    if len(chinese) == 1:
        grams.append(chinese)
    words = re.findall(r"[a-z0-9][a-z0-9_+.#-]*", normalized)
    return Counter(grams + words)


class EvidenceRetriever:
    """无需向量数据库的页级混合检索器，便于离线演示与部署。"""

    def __init__(self, slides: list[SlideContent]):
        self.chunks = [
            SourceChunk(
                page=slide.number,
                title=slide.title or f"第{slide.number}页",
                content=slide.evidence_text(),
            )
            for slide in slides
            if slide.evidence_text().strip()
        ]
        self.features = [_features(f"{chunk.title}\n{chunk.content}") for chunk in self.chunks]
        self.document_frequency: Counter[str] = Counter()
        for features in self.features:
            self.document_frequency.update(features.keys())

    def search(self, query: str, top_k: int = 5) -> list[SourceChunk]:
        q = _features(query)
        if not q or not self.chunks:
            return []
        n = len(self.chunks)
        scored: list[SourceChunk] = []
        for chunk, features in zip(self.chunks, self.features):
            dot = 0.0
            q_norm = 0.0
            d_norm = 0.0
            for token, q_count in q.items():
                idf = math.log((n + 1) / (self.document_frequency[token] + 1)) + 1.0
                q_weight = (1 + math.log(q_count)) * idf
                d_count = features.get(token, 0)
                d_weight = (1 + math.log(d_count)) * idf if d_count else 0.0
                dot += q_weight * d_weight
                q_norm += q_weight * q_weight
            for token, d_count in features.items():
                idf = math.log((n + 1) / (self.document_frequency[token] + 1)) + 1.0
                d_weight = (1 + math.log(d_count)) * idf
                d_norm += d_weight * d_weight
            score = dot / (math.sqrt(q_norm) * math.sqrt(d_norm) + 1e-9)
            if _normalize(query) in _normalize(chunk.content):
                score += 0.35
            if score > 0:
                scored.append(
                    SourceChunk(
                        page=chunk.page,
                        title=chunk.title,
                        content=chunk.content,
                        kind=chunk.kind,
                        score=score,
                    )
                )
        return sorted(scored, key=lambda item: (-item.score, item.page))[:top_k]

    @staticmethod
    def format_context(chunks: list[SourceChunk], max_chars: int = 12_000) -> str:
        blocks: list[str] = []
        total = 0
        for chunk in chunks:
            block = f"{chunk.citation} {chunk.title}\n{chunk.content.strip()}"
            if total + len(block) > max_chars:
                break
            blocks.append(block)
            total += len(block)
        return "\n\n".join(blocks)

