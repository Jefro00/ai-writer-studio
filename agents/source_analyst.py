"""Deterministic source metadata and quality signals (not truth guarantees)."""
from __future__ import annotations
from urllib.parse import urlsplit

OFFICIAL_HINTS = (".gov", ".edu", "sec.gov", "federalreserve", "ecb.europa", "docs.", "developer.", "foundation", "official")


def assess_source(source: dict) -> dict:
    try:
        host = (urlsplit(source.get("url", "")).hostname or "").lower()
    except ValueError:
        host = ""
    text_len = len((source.get("content") or "").strip())
    official = any(hint in host for hint in OFFICIAL_HINTS)
    source_type = "primary/official candidate" if official else "secondary or unclassified"
    notes = []
    score = 0
    if official:
        score += 2
        notes.append("Домен выглядит официальным; это не подтверждает точность конкретного утверждения.")
    else:
        notes.append("Официальность домена автоматически не подтверждена.")
    if source.get("published_at"):
        score += 1
        notes.append(f"Дата публикации обнаружена: {source['published_at']}.")
    else:
        notes.append("Дата публикации не обнаружена.")
    if text_len >= 1200:
        score += 1
        notes.append("Получен полный текст страницы.")
    elif text_len:
        notes.append("Извлечённый текст короткий.")
    else:
        notes.append("Полный текст недоступен; используется только поисковый сниппет.")
    return {**source, "source_type": source_type, "quality_signal": score, "credibility_notes": " ".join(notes)}


def assess_sources(sources: list[dict]) -> list[dict]:
    return [assess_source(source) for source in sources]
