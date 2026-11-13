"""Markdown and DOCX export helpers."""
from __future__ import annotations
import io
import re


def create_markdown(article: str, sources: list[dict], checks: list[dict] | None = None) -> str:
    text = article.rstrip()
    if sources:
        text += "\n\n## Sources\n\n" + "\n".join(f"{i}. [{s.get('title') or 'Source'}]({s.get('url','')})" + (f" — published {s['published_at']}" if s.get("published_at") else "") for i, s in enumerate(sources, 1))
    if checks:
        text += "\n\n## Fact-check notes\n\n" + "\n".join(f"- **{c['status']}** — {c['claim']}" + (f" [source {', '.join(map(str, c['source_ids']))}]" if c.get("source_ids") else "") + (f" — {c['note']}" if c.get("note") else "") for c in checks)
    return text + "\n"


def create_docx(markdown: str) -> bytes:
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            doc.add_heading(heading.group(2), level=len(heading.group(1)))
        elif re.match(r"^[-*+]\s+", line):
            doc.add_paragraph(re.sub(r"^[-*+]\s+", "", line), style="List Bullet")
        elif re.match(r"^\d+[.)]\s+", line):
            doc.add_paragraph(re.sub(r"^\d+[.)]\s+", "", line), style="List Number")
        else:
            paragraph = doc.add_paragraph()
            # Word keeps the source URL/reference text; strip basic markdown emphasis only.
            paragraph.add_run(re.sub(r"(?<!\\)[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", line).replace("\\*", "*"))
            for run in paragraph.runs:
                run.font.size = Pt(10.5)
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
