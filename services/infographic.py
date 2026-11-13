"""Accessible, source-linked responsive SVG evidence cards."""
from __future__ import annotations

import html
import textwrap

DESKTOP_WIDTH = 1200
DESKTOP_PAD = 64
MOBILE_WIDTH = 390
MOBILE_PAD = 18


def _wrap(text: str, width: int) -> list[str]:
    lines = textwrap.wrap(str(text), width=width, break_long_words=True,
                         break_on_hyphens=True, replace_whitespace=True)
    return lines or [""]


def card_height(card: dict, mobile: bool = False) -> int:
    items = card.get("items", [])[:4]
    if mobile:
        subtitle_lines = _wrap("Факты приведены без пересказа; номера ведут к источникам в проекте.", 46)
        first_item_y = 127 + len(subtitle_lines) * 18 + 16
        item_heights = [max(140, len(_wrap(item.get("claim", ""), 40)) * 23 + 88) for item in items]
        items_end = first_item_y + sum(item_heights) + max(0, len(items) - 1) * 12
        footer_lines = _wrap(card.get("disclaimer", "Автоматическая проверка; перепроверьте первоисточники."), 36)
        return max(440, items_end + 22 + len(footer_lines) * 18 + 36)
    item_heights = [max(116, len(_wrap(item.get("claim", ""), 88)) * 30 + 72) for item in items]
    footer_y = 202 + sum(item_heights) + max(0, len(items) - 1) * 16 + 72
    return max(520, footer_y + 74)


def render_svg(card: dict, mobile: bool = False) -> str:
    """Render a single editorial fact card as self-contained, scalable SVG."""
    items = card.get("items", [])[:4]
    if mobile:
        width, pad, wrap_chars = MOBILE_WIDTH, MOBILE_PAD, 40
        height = card_height(card, mobile=True)
        title_y, title_size = 98, 24
        subtitle_lines = _wrap("Факты приведены без пересказа; номера ведут к источникам в проекте.", 46)
        first_item_y = 127 + len(subtitle_lines) * 18 + 16
        line_height, body_size = 23, 16
        item_heights = [max(140, len(_wrap(item.get("claim", ""), wrap_chars)) * line_height + 88) for item in items]
        title_font = "24px"
    else:
        width, pad, wrap_chars = DESKTOP_WIDTH, DESKTOP_PAD, 88
        height = card_height(card)
        title_y, title_size = 142, 34
        subtitle_lines = ["Факты приведены без пересказа; номера ведут к источникам в проекте."]
        first_item_y = 202
        line_height, body_size = 30, 20
        item_heights = [max(116, len(_wrap(item.get("claim", ""), wrap_chars)) * line_height + 72) for item in items]
        title_font = "34px"

    prepared = [(item, _wrap(item.get("claim", ""), wrap_chars)) for item in items]
    uid = "mobile" if mobile else "desktop"
    subtitle = "Факты приведены без пересказа; номера ведут к источникам в проекте."
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="card-title-{uid} card-desc-{uid}">',
        f'<title id="card-title-{uid}">Инфографика: факты по теме</title>',
        f'<desc id="card-desc-{uid}">Карточка содержит дословные утверждения с номерами источников и отметкой автоматической проверки.</desc>',
        f'<rect width="{width}" height="{height}" fill="#F9F8F7"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="{height - 16}" rx="16" fill="#FFFFFF" stroke="#E6E5E3" stroke-width="1.5"/>',
        f'<rect x="{pad}" y="40" width="5" height="25" rx="2.5" fill="#2783DE"/>',
        f'<text x="{pad + 14}" y="57" font-family="Arial, sans-serif" font-size="10" font-weight="700" letter-spacing=".8" fill="#5D6872">AI WRITER STUDIO  ·  RESEARCH CARD</text>',
        f'<text x="{pad}" y="{title_y}" font-family="Arial, sans-serif" font-size="{title_font}" font-weight="700" fill="#2C2C2B">Что показывают источники</text>',
    ]
    if mobile:
        subtitle_y = 122
        for line in subtitle_lines:
            parts.append(f'<text x="{pad}" y="{subtitle_y}" font-family="Arial, sans-serif" font-size="13" fill="#6B6A67">{html.escape(line)}</text>')
            subtitle_y += 18
    else:
        parts.append(f'<text x="{pad}" y="174" font-family="Arial, sans-serif" font-size="17" fill="#6B6A67">{html.escape(subtitle)}</text>')

    y = first_item_y
    for index, (item, lines) in enumerate(prepared, start=1):
        item_height = item_heights[index - 1]
        parts.append(f'<rect x="{pad}" y="{y}" width="{width - pad * 2}" height="{item_height}" rx="12" fill="#F9F8F7" stroke="#E6E5E3"/>')
        if mobile:
            cx, cy, radius = pad + 18, y + 27, 13
            number_size, number_y = 13, y + 32
            badge_text = "ПРОВЕРЕНО" if item.get("status") == "VERIFIED" else "ЧАСТИЧНО"
            badge_w = 100 if item.get("status") == "VERIFIED" else 94
            badge_h, badge_font, badge_y = 21, 12, y + 13
            badge_x = width - pad - badge_w - 10
            claim_x, claim_y = pad + 16, y + 62
            source_size, source_x = 14, pad + 16
        else:
            cx, cy, radius = pad + 28, y + 31, 16
            number_size, number_y = 16, y + 37
            badge_text = "ПРОВЕРЕНО МОДЕЛЬЮ" if item.get("status") == "VERIFIED" else "ЧАСТИЧНО ПОДТВЕРЖДЕНО"
            badge_w = 190 if item.get("status") == "VERIFIED" else 245
            badge_h, badge_font, badge_y = 26, 12, y + 16
            badge_x = width - pad - badge_w - 18
            claim_x, claim_y = pad + 58, y + 66
            source_size, source_x = 14, pad + 58
        parts.extend([
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#E5F2FC"/>',
            f'<text x="{cx}" y="{number_y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{number_size}" font-weight="700" fill="#1769AA">{index}</text>',
        ])
        badge_fill = "#E8F1EC" if item.get("status") == "VERIFIED" else "#FBEBDE"
        badge_color = "#347A53" if item.get("status") == "VERIFIED" else "#93551F"
        parts.extend([
            f'<rect x="{badge_x}" y="{badge_y}" width="{badge_w}" height="{badge_h}" rx="6" fill="{badge_fill}"/>',
            f'<text x="{badge_x + 8}" y="{badge_y + badge_h - (6 if mobile else 8)}" font-family="Arial, sans-serif" font-size="{badge_font}" font-weight="700" letter-spacing=".2" fill="{badge_color}">{badge_text}</text>',
        ])
        text_y = claim_y
        for line in lines:
            parts.append(f'<text x="{claim_x}" y="{text_y}" font-family="Arial, sans-serif" font-size="{body_size}" fill="#2C2C2B">{html.escape(line)}</text>')
            text_y += line_height
        refs = ", ".join(f"[{value}]" for value in item.get("source_ids", [])) or "источники не указаны"
        parts.append(f'<text x="{source_x}" y="{y + item_height - (12 if mobile else 16)}" font-family="Arial, sans-serif" font-size="{source_size}" fill="#6B6A67">ИСТОЧНИКИ  {html.escape(refs)}</text>')
        y += item_height + (12 if mobile else 16)

    disclaimer = card.get("disclaimer", "Автоматическая проверка; перепроверьте первоисточники.")
    if mobile:
        separator_y = height - 22 - len(_wrap(disclaimer, 36)) * 18 - 8
        parts.append(f'<line x1="{pad}" y1="{separator_y}" x2="{width - pad}" y2="{separator_y}" stroke="#E6E5E3"/>')
        footer_y = separator_y + 21
        for line in _wrap(disclaimer, 36):
            parts.append(f'<text x="{pad}" y="{footer_y}" font-family="Arial, sans-serif" font-size="14" fill="#6B6A67">{html.escape(line)}</text>')
            footer_y += 18
    else:
        separator_y = height - 90
        parts.extend([
            f'<line x1="{pad}" y1="{separator_y}" x2="{width - pad}" y2="{separator_y}" stroke="#E6E5E3"/>',
            f'<text x="{pad}" y="{height - 57}" font-family="Arial, sans-serif" font-size="14" fill="#6B6A67">{html.escape(disclaimer)}</text>',
        ])
    parts.append("</svg>")
    return "\n".join(parts)


def render_html(card: dict) -> str:
    desktop_svg = render_svg(card)
    mobile_svg = render_svg(card, mobile=True)
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body{{margin:0;padding:0;background:#F9F8F7;font-family:Arial,sans-serif}}
main{{width:100%;max-width:1200px;margin:0 auto}}
svg{{display:block;width:100%;height:auto}}
.mobile{{display:none}}
@media(max-width:560px){{.desktop{{display:none}}.mobile{{display:block}}}}
@media(prefers-color-scheme:dark){{html,body{{background:#191919}}}}
</style></head><body><main><div class="desktop">{desktop_svg}</div><div class="mobile">{mobile_svg}</div></main></body></html>"""
