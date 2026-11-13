"""Editorial review that preserves evidence and flags unresolved claims."""


def edit(article: str, analysis: str, checks: list[dict], ai) -> str:
    checks_text = "\n".join(f"- {c['status']}: {c['claim']} — {c.get('note','')} (sources: {c.get('source_ids',[])})" for c in checks)
    prompt = f"""You are the final editor of a research-driven publication. Improve clarity, structure, grammar, and consistency in the draft. Do not add unsupported facts, numbers, dates, quotations, or citations. Preserve source references. Where fact-checking identifies an important UNVERIFIED or PARTIALLY VERIFIED claim, qualify it or remove it if it is not essential. Keep the requested format and language. Return only the complete edited Markdown draft.
DRAFT:\n<<<\n{article}\n>>>\nFACT-CHECK NOTES:\n{checks_text or 'No parsed checks available; do not infer verification.'}\nRESEARCH DOSSIER:\n{analysis[:12000]}"""
    return ai.ask(prompt, "Editor")
