from __future__ import annotations

import html
from datetime import datetime

from .models import StudyPack


def _markdown(text: str) -> str:
    try:
        import markdown

        return markdown.markdown(text or "", extensions=["extra", "tables", "fenced_code", "sane_lists"])
    except ImportError:
        return "".join(f"<p>{html.escape(line)}</p>" for line in (text or "").splitlines() if line.strip())


def render_study_html(pack: StudyPack) -> str:
    sections = [
        ("学习概览", pack.overview),
        ("必要背景知识", pack.background_knowledge),
        ("知识地图", pack.knowledge_map),
        ("完整复习解析", pack.detailed_notes),
        ("重点与掌握标准", pack.key_points),
        ("易错点与核对提醒", pack.common_pitfalls),
        ("复习计划", pack.review_plan),
    ]
    section_html = "\n".join(
        f'<section><div class="eyebrow">{index:02d}</div><h2>{html.escape(title)}</h2>{_markdown(body)}</section>'
        for index, (title, body) in enumerate(sections, start=1)
    )
    quiz_html_parts: list[str] = []
    for index, item in enumerate(pack.quiz, start=1):
        options = "".join(f"<li>{html.escape(option)}</li>" for option in item.options)
        citations = " · ".join(html.escape(c) for c in item.citations)
        quiz_html_parts.append(
            f"""
            <article class="quiz-card">
              <div class="quiz-meta">{html.escape(item.question_type)} · {html.escape(item.difficulty)} · Q{index:02d}</div>
              <h3>{html.escape(item.question)}</h3>
              {f'<ol class="options">{options}</ol>' if options else ''}
              <details><summary>查看答案与解析</summary>
                <p><strong>答案：</strong>{html.escape(item.answer)}</p>
                <div>{_markdown(item.explanation)}</div>
                <p class="citation">证据：{citations or '课件综合内容'}</p>
              </details>
            </article>
            """
        )
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(pack.course_title)}｜课析 StudyLens</title>
<style>
:root{{--ink:#15211e;--muted:#62716c;--paper:#f7f4ec;--card:#fffdf8;--line:#dcd8cc;--teal:#0d756b;--amber:#e9a23b}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.85 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Noto Sans CJK SC",sans-serif}}
.shell{{max-width:1040px;margin:auto;padding:36px 28px 100px}} .hero{{padding:64px;border:1px solid var(--line);border-radius:28px;background:linear-gradient(135deg,#fffdf8 0%,#edf7f2 100%);box-shadow:0 20px 70px rgba(35,54,48,.08)}}
.brand,.eyebrow,.quiz-meta{{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--teal);font-weight:750}} h1{{font:700 clamp(38px,6vw,72px)/1.08 Georgia,"Noto Serif CJK SC",serif;margin:.25em 0}} .dek{{font-size:20px;color:var(--muted);max-width:760px}}
.meta{{margin-top:30px;color:var(--muted);font-size:14px}} section{{margin-top:28px;padding:44px 52px;background:var(--card);border:1px solid var(--line);border-radius:22px}} h2{{font:700 30px/1.3 Georgia,"Noto Serif CJK SC",serif;margin:.2em 0 1em}} h3{{line-height:1.45}} blockquote{{margin:1.4em 0;padding:14px 20px;border-left:4px solid var(--amber);background:#fff5df;color:#5c4b2c}} code{{background:#edf2ef;padding:.1em .35em;border-radius:5px}} table{{border-collapse:collapse;width:100%;font-size:15px}} th,td{{border:1px solid var(--line);padding:10px 12px;text-align:left}} th{{background:#eef5f1}}
.quiz-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}} .quiz-card{{padding:25px;border:1px solid var(--line);border-radius:18px;background:var(--card)}} details{{border-top:1px solid var(--line);margin-top:20px;padding-top:14px}} summary{{cursor:pointer;font-weight:700;color:var(--teal)}} .citation{{color:var(--muted);font-size:14px}}
.print{{position:fixed;right:24px;bottom:24px;border:0;border-radius:999px;padding:13px 20px;background:var(--teal);color:white;font-weight:700;cursor:pointer;box-shadow:0 12px 30px rgba(13,117,107,.25)}}
@media(max-width:680px){{.shell{{padding:16px 12px 80px}}.hero,section{{padding:28px 22px}}}} @media print{{body{{background:white}}.shell{{max-width:none;padding:0}}.hero,section,.quiz-card{{box-shadow:none;break-inside:avoid}}.print{{display:none}}}}
</style>
</head>
<body><main class="shell">
<header class="hero"><div class="brand">StudyLens · 课析</div><h1>{html.escape(pack.course_title)}</h1><p class="dek">{html.escape(pack.one_sentence_summary)}</p><div class="meta">共 {pack.source_pages} 页课件 · {html.escape(pack.generated_by)} · 生成于 {generated}</div></header>
{section_html}
<section><div class="eyebrow">08</div><h2>复习题与答案</h2><div class="quiz-grid">{''.join(quiz_html_parts)}</div></section>
</main><button class="print" onclick="window.print()">打印 / 导出 PDF</button></body></html>"""
