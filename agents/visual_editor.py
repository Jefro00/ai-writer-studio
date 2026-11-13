"""Selects evidence-backed claims for a concise infographic card."""
from __future__ import annotations

import json
import re

from agents.fact_checker import ALLOWED


def _parse_json(raw: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def recommend_cards(topic: str, article: str, checks: list[dict], ai) -> list[dict]:
    """Ask whether a visual adds value; render only verbatim checked claims."""
    eligible = [
        (index, check)
        for index, check in enumerate(checks, start=1)
        if check.get("status") in ALLOWED
        and check.get("status") in {"VERIFIED", "PARTIALLY VERIFIED"}
        and check.get("claim")
    ]
    if len(eligible) < 2:
        return []

    evidence = "\n".join(
        f"CHECK_ID={index} | STATUS={check['status']} | CLAIM={check['claim']} | "
        f"SOURCE_IDS={check.get('source_ids', [])}"
        for index, check in eligible
    )
    prompt = f"""You are an infographic editor. Decide whether one small evidence card would materially improve the reader's understanding of this article. If not, return {{\"cards\":[]}}.
Return only JSON shaped as {{\"cards\":[{{\"check_ids\":[1,2]}}]}}. Include at most 2 non-overlapping cards; each must group 2–4 check IDs from the supplied list. Select only claims that are genuinely clearer together (e.g. a small set of related facts). Do not write or paraphrase claims, titles, numbers, dates, or labels; the application will render the exact checked claim text. Never create a card just to decorate the article.

TOPIC: {topic}
ARTICLE:
<<<
{article[:12000]}
>>>
ELIGIBLE CHECKED CLAIMS:
{evidence}"""
    raw = ai.ask(prompt, "Infographic Editor")
    data = _parse_json(raw)
    rows = data.get("cards", []) if isinstance(data, dict) else []
    cards = []
    used: set[int] = set()
    by_id = dict(eligible)
    for row in rows[:2] if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("check_ids"), list):
            continue
        ids = []
        for value in row["check_ids"]:
            try:
                check_id = int(value)
            except (TypeError, ValueError):
                continue
            if check_id in by_id and check_id not in used and check_id not in ids:
                ids.append(check_id)
        if len(ids) < 2:
            continue
        used.update(ids)
        items = []
        source_ids = set()
        for check_id in ids:
            check = by_id[check_id]
            valid_source_ids = []
            for source_id in check.get("source_ids", []):
                try:
                    source_id = int(source_id)
                    if source_id > 0 and source_id not in valid_source_ids:
                        valid_source_ids.append(source_id)
                        source_ids.add(source_id)
                except (TypeError, ValueError):
                    pass
            items.append({
                "claim": str(check["claim"]).strip(),
                "status": check["status"],
                "source_ids": valid_source_ids,
            })
        cards.append({
            "title": "Что показывают источники",
            "items": items,
            "source_ids": sorted(source_ids),
            "disclaimer": "Автоматическая проверка по доступным источникам; перепроверьте первоисточники.",
        })
    return cards