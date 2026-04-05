import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RawArticle:
    url: str
    title: str
    source_name: str
    source_type: str  # reddit / rss / blog / twitter
    raw_text: str = ""
    published_at: datetime | None = None
    extra: dict = field(default_factory=dict)


class BaseScraper(ABC):
    source_name: str = "Unknown"
    source_type: str = "unknown"

    async def scrape(self) -> list[RawArticle]:
        try:
            articles = await self._fetch()
            logger.info(f"[{self.source_name}] fetched {len(articles)} articles")
            return articles
        except Exception as exc:
            logger.warning(f"[{self.source_name}] scrape failed: {exc}")
            return []

    @abstractmethod
    async def _fetch(self) -> list[RawArticle]:
        ...
