"""Format-aware content production with explicit source links."""
from __future__ import annotations


def write(topic: str, analysis: str, strategy: str, sources: list[dict], content_format: str, language: str, style: str, length: int, ai) -> str:
    source_list = "\n".join(f"[{i}] {s.get('title','Untitled')} — {s.get('url','')} (date: {s.get('published_at') or 'unknown'})" for i, s in enumerate(sources, 1))
    format_rules = {
        "X Article": f"Write an X-ready long-form article around {length} words, with headline, concise lead, clear sections, caveats, conclusion, and numbered citations.",
        "Thread": "Write a numbered X thread of 8–12 concise posts. Each post must stand on its own; first post is a clear hook, final post includes caveat or sources. Keep each post comfortably below 280 characters where practical.",
        "Single Post": "Write one compact X post, preferably under 280 characters, with one clear insight and no unsupported claim. Include a source URL if space allows.",
        "Research Post": "Write a concise research-led X post (or short multi-paragraph post) with key evidence, dates, source citations, uncertainty, and no hype.",
        "Market Commentary": "Write balanced market commentary: what changed, evidence, plausible interpretation, counterpoint, and risks. Clearly label opinions and forecasts.",
    }.get(content_format, f"Write a well-structured article of approximately {length} words.")
    prompt = f"""You are a professional research-driven writer for X.
TOPIC: {topic}
LANGUAGE: {language}
STYLE: {style}
FORMAT: {content_format}
TASK: {format_rules}

EDITORIAL BRIEF:
{strategy}

RESEARCH DOSSIER:
{analysis}

AVAILABLE SOURCES:
{source_list}

Rules: research first, verify second, write third. Never invent facts, metrics, quotes, citations, or dates. Use numbered references [1] only for sources that support the claim; do not cite merely because a source is in the list. Be transparent that some evidence may come from search snippets. Avoid generic AI introductions and promotional language. Return only the final draft in Markdown. For threads, prefix each post with its number and separate posts with blank lines."""
    return ai.ask(prompt, "Writer")
