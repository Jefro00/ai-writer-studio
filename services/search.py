"""DuckDuckGo web search with URL deduplication."""
from __future__ import annotations


def search_web(topic: str, max_results: int = 5) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError("Установите ddgs для веб-поиска") from exc
    queries = [topic, f"{topic} latest data official", f"{topic} analysis research"]
    results: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    for query in queries:
        try:
            with DDGS() as search:
                found = search.text(query, max_results=max_results)
            for row in found or []:
                url = (row.get("href") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                results.append({"title": (row.get("title") or "").strip(), "url": url,
                                "snippet": (row.get("body") or "").strip(), "query": query})
        except Exception as exc:
            errors.append(str(exc))
    if not results and errors:
        raise RuntimeError("Поиск не сработал: " + errors[-1][:300])
    return results
