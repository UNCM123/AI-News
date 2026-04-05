import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

CATEGORIES = ["Models & Research", "Products & Tools", "Industry News", "Community"]

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def summarize_article(title: str, text: str, source: str) -> tuple[str, str]:
    """Returns (2-3 sentence summary, category)."""
    if not settings.anthropic_api_key:
        return ("No summary available (ANTHROPIC_API_KEY not set).", "Industry News")

    prompt = f"""You are an AI news editor. Given the article below, do two things:
1. Write a 2-3 sentence summary that captures the key point clearly and concisely.
2. Classify it into exactly one of these categories: {", ".join(CATEGORIES)}

Source: {source}
Title: {title}
Content: {text[:3000]}

Respond in this exact format:
SUMMARY: <your summary>
CATEGORY: <one category from the list>"""

    try:
        msg = await get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        response = msg.content[0].text.strip()
        summary = ""
        category = "Industry News"
        for line in response.splitlines():
            if line.startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):].strip()
            elif line.startswith("CATEGORY:"):
                cat = line[len("CATEGORY:"):].strip()
                if cat in CATEGORIES:
                    category = cat
        return summary or "No summary generated.", category
    except Exception as exc:
        logger.warning(f"[Summarizer] article summarization failed: {exc}")
        return ("Summary unavailable.", "Industry News")


async def generate_digest_summary(articles_by_category: dict[str, list]) -> str:
    """Returns a 3-4 sentence overview of the day's biggest AI developments."""
    if not settings.anthropic_api_key:
        return "AI digest summary unavailable (ANTHROPIC_API_KEY not set)."

    lines = []
    for cat, articles in articles_by_category.items():
        if articles:
            lines.append(f"\n{cat}:")
            for a in articles[:5]:
                lines.append(f"  - {a.title}: {a.summary or ''}")

    if not lines:
        return "No articles collected yet."

    prompt = f"""You are an AI news editor writing a daily briefing.
Based on today's AI news headlines below, write a 3-4 sentence executive summary highlighting the most significant developments.
Be specific, insightful, and engaging.

Today's headlines:
{"".join(lines)}

Write only the summary paragraph, no labels or headings."""

    try:
        msg = await get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning(f"[Summarizer] digest summary failed: {exc}")
        return "Today's AI news digest is ready. Browse the categories below."
