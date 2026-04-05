import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser

from app.config import settings
from app.scrapers.base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    # --- AI News Sites ---
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Import AI", "https://jack-clark.net/feed/"),
    # --- Major AI Company Blogs ---
    ("Anthropic Blog", "https://www.anthropic.com/rss.xml"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("Google Gemini", "https://blog.google/products/gemini/rss/"),
    ("Meta AI Blog", "https://ai.meta.com/blog/rss/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Mistral AI", "https://mistral.ai/news/rss"),
    ("Microsoft AI Blog", "https://blogs.microsoft.com/ai/feed/"),
    ("GitHub AI/ML Blog", "https://github.blog/category/ai-ml/feed/"),
    ("AWS Machine Learning", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("NVIDIA AI Blog", "https://blogs.nvidia.com/blog/category/deep-learning-ai/feed/"),
    ("Cohere Blog", "https://cohere.com/blog/rss"),
    ("Stability AI", "https://stability.ai/news/rss"),
    ("ElevenLabs Blog", "https://elevenlabs.io/blog/rss.xml"),
    ("Perplexity Blog", "https://blog.perplexity.ai/rss"),
    ("Runway ML Blog", "https://runwayml.com/blog/rss"),
    ("Cursor Blog", "https://cursor.com/blog/rss"),
]


def _parse_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
    return None


class RssScraper(BaseScraper):
    source_type = "rss"

    def __init__(self, source_name: str, feed_url: str):
        self.source_name = source_name
        self._feed_url = feed_url

    async def _fetch(self) -> list[RawArticle]:
        return await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> list[RawArticle]:
        feed = feedparser.parse(self._feed_url)
        articles = []
        limit = settings.max_articles_per_source
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for entry in feed.entries[:limit]:
            url = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not url or not title:
                continue

            published_at = _parse_date(entry)
            # Skip articles older than 24 hours (if date is available)
            if published_at:
                pub_utc = published_at.replace(tzinfo=timezone.utc)
                if pub_utc < cutoff:
                    continue

            summary = entry.get("summary", "") or entry.get("description", "")
            content_list = entry.get("content", [])
            full_text = content_list[0].get("value", "") if content_list else summary
            clean = re.sub(r"<[^>]+>", " ", full_text or summary)
            clean = re.sub(r"\s+", " ", clean).strip()

            articles.append(
                RawArticle(
                    url=url,
                    title=title,
                    source_name=self.source_name,
                    source_type="rss",
                    raw_text=clean[:4000],
                    published_at=published_at,
                )
            )
        return articles


async def scrape_all_rss() -> list[RawArticle]:
    scrapers = [RssScraper(name, url) for name, url in RSS_SOURCES]
    results = await asyncio.gather(*[s.scrape() for s in scrapers])
    return [a for batch in results for a in batch]
