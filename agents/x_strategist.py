"""Editorial angle and format-specific structure planning."""

FORMATS = ("X Article", "Thread", "Single Post", "Research Post", "Market Commentary")


def plan(topic: str, analysis: str, content_format: str, style: str, language: str, ai) -> str:
    prompt = f"""You are an X editorial strategist. Create a short evidence-led writing brief, not the final content.
Topic: {topic}
Format: {content_format}
Style: {style}
Language: {language}
Research dossier:
{analysis}

Return: one-sentence angle, intended audience, hook, ordered structure appropriate to the format, key evidence with source numbers, caveats, and a concise CTA only if natural. Avoid hype and engagement bait. Never add claims absent from the dossier."""
    return ai.ask(prompt, "X Strategist")
