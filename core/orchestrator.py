"""End-to-end, auditable research and writing pipeline."""
from __future__ import annotations
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents import editor, fact_checker, research_manager, source_analyst, visual_editor, writer, x_strategist
from services.search import search_web
from services.web_reader import enrich_source


def run_editorial(topic: str, language: str, style: str, length: int, content_format: str, ai, max_source_fetches: int = 8, make_infographics: bool = True, progress=None) -> dict:
    def emit(stage, message):
        if progress:
            progress(stage, message)
    emit("search", "Ищу источники по нескольким запросам")
    raw_sources = search_web(topic)
    if not raw_sources:
        raise RuntimeError("Не удалось найти источники. Попробуйте уточнить тему.")
    emit("extract", f"Извлекаю содержимое страниц (до {min(len(raw_sources), max_source_fetches)})")
    fetched = raw_sources[:max_source_fetches]
    enriched_by_index = {}
    # Bounded concurrency prevents slow sites from serializing the whole run.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(enrich_source, source): idx for idx, source in enumerate(fetched)}
        for future in as_completed(futures):
            enriched_by_index[futures[future]] = future.result()
            emit("extract", f"Обработано страниц: {len(enriched_by_index)}/{len(fetched)}")
    sources = [enriched_by_index[i] for i in range(len(fetched))]
    sources.extend(raw_sources[max_source_fetches:])
    sources = source_analyst.assess_sources(sources)
    emit("analysis", "Синтезирую рыночные, проектные и институциональные данные")
    analysis = research_manager.analyze(topic, sources, ai)
    emit("strategy", "Формирую угол подачи и структуру")
    strategy = x_strategist.plan(topic, analysis, content_format, style, language, ai)
    emit("writing", "Пишу материал в выбранном формате")
    draft = writer.write(topic, analysis, strategy, sources, content_format, language, style, length, ai)
    emit("fact_check", "Проверяю ключевые утверждения по собранным источникам")
    checks = fact_checker.check_claims(draft, analysis, sources, ai)
    infographics = []
    infographic_note = ""
    if make_infographics and sum(c.get("status") in {"VERIFIED", "PARTIALLY VERIFIED"} for c in checks) >= 2:
        emit("infographic", "Проверяю, поможет ли читателю инфографика")
        try:
            infographics = visual_editor.recommend_cards(topic, draft, checks, ai)
        except Exception as exc:
            # A visual-generation failure must not discard a useful article.
            infographic_note = str(exc)[:240]
    emit("editing", "Редактирую текст с учётом результатов проверки")
    article = editor.edit(draft, analysis, checks, ai)
    emit("done", "Черновик готов")
    return {"topic": topic, "language": language, "style": style, "length": length,
            "content_format": content_format, "analysis": analysis, "strategy": strategy,
            "draft": draft, "article": article, "sources": sources, "fact_checks": checks,
            "infographics": infographics, "infographic_note": infographic_note,
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "status": "draft", "published_url": ""}
