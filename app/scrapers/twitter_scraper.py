import asyncio
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from app.config import settings
from app.scrapers.base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

# Nitter instances to try in order
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

AI_ACCOUNTS = [
    "AnthropicAI",
    "OpenAI",
    "GoogleDeepMind",
    "MetaAI",
    "huggingface",
    "MistralAI",
    "xai",
    "lovable_dev",
    "cursor_ai",
    "perplexity_ai",
    "ylecun",
    "karpathy",
    "sama",
    "demishassabis",
    "nvidia",
    "runwayml",
    "ElevenLabsio",
]


def _parse_nitter_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                pass
    return None


def _clean_tweet(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"\s+", " ", text).strip()


class TwitterScraper(BaseScraper):
    source_type = "twitter"

    def __init__(self, account: str):
        self.source_name = f"@{account} (Twitter/X)"
        self._account = account

    async def _fetch(self) -> list[RawArticle]:
        return await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> list[RawArticle]:
        limit = min(settings.max_articles_per_source, 10)

        for instance in NITTER_INSTANCES:
            feed_url = f"{instance}/{self._account}/rss"
            try:
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    continue
                articles = []
                for entry in feed.entries[:limit]:
                    url = entry.get("link", "")
                    title = entry.get("title", "").strip()
                    summary = _clean_tweet(entry.get("summary", "") or title)
                    if not url or not summary:
                        continue
                    articles.append(
                        RawArticle(
                            url=url,
                            title=title[:200],
                            source_name=self.source_name,
                            source_type="twitter",
                            raw_text=summary[:2000],
                            published_at=_parse_nitter_date(entry),
                        )
                    )
                return articles
            except Exception as exc:
                logger.debug(f"[Twitter] {self._account} on {instance} failed: {exc}")
                continue

        logger.warning(f"[Twitter] @{self._account}: all nitter instances failed, skipping")
        return []


async def scrape_all_twitter() -> list[RawArticle]:
    scrapers = [TwitterScraper(account) for account in AI_ACCOUNTS]
    results = await asyncio.gather(*[s.scrape() for s in scrapers])
    return [a for batch in results for a in batch]
