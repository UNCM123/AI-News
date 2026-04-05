import asyncio
import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.scrapers.base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# (source_name, listing_url, article_link_selector, title_selector, text_selector)
BLOG_SOURCES = [
    {
        "name": "xAI (Grok)",
        "url": "https://x.ai/news",
        "link_css": "a[href*='/news/']",
        "base_url": "https://x.ai",
    },
    {
        "name": "Lovable.dev Blog",
        "url": "https://lovable.dev/blog",
        "link_css": "a[href*='/blog/']",
        "base_url": "https://lovable.dev",
    },
    {
        "name": "StackBlitz Blog",
        "url": "https://blog.stackblitz.com",
        "link_css": "a[href*='/post/'], a[href*='/blog/'], article a",
        "base_url": "https://blog.stackblitz.com",
    },
    {
        "name": "Replit Blog",
        "url": "https://blog.replit.com",
        "link_css": "a[href*='/blog/'], article a",
        "base_url": "https://blog.replit.com",
    },
    {
        "name": "Character.AI Blog",
        "url": "https://blog.character.ai",
        "link_css": "a[href*='/p/'], article a",
        "base_url": "",
    },
    {
        "name": "Midjourney Updates",
        "url": "https://www.midjourney.com/updates",
        "link_css": "a[href*='/updates/']",
        "base_url": "https://www.midjourney.com",
    },
    {
        "name": "Adobe Firefly Blog",
        "url": "https://blog.adobe.com/en/topics/firefly",
        "link_css": "a[href*='/en/publish/'], a[href*='blog.adobe.com']",
        "base_url": "https://blog.adobe.com",
    },
]


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    article = soup.find("article") or soup.find("main") or soup.body
    if not article:
        return ""
    text = article.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)[:4000]


def _extract_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title")
    return tag.get_text(strip=True) if tag else ""


async def _fetch_article(client: httpx.AsyncClient, url: str, source_name: str) -> RawArticle | None:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        title = _extract_title(soup)
        text = _extract_text(soup)
        if not title:
            return None
        return RawArticle(url=url, title=title, source_name=source_name, source_type="blog", raw_text=text)
    except Exception as exc:
        logger.debug(f"[Blog] fetch {url} failed: {exc}")
        return None


class BlogScraper(BaseScraper):
    source_type = "blog"

    def __init__(self, config: dict):
        self.source_name = config["name"]
        self._config = config

    async def _fetch(self) -> list[RawArticle]:
        cfg = self._config
        limit = settings.max_articles_per_source

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.get(cfg["url"], headers=HEADERS, follow_redirects=True)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, "lxml")
                links = soup.select(cfg["link_css"])
                seen: set[str] = set()
                article_urls: list[str] = []
                for a in links[:limit * 2]:
                    href = a.get("href", "")
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = cfg["base_url"] + href
                    elif not href.startswith("http"):
                        continue
                    if href not in seen and href != cfg["url"]:
                        seen.add(href)
                        article_urls.append(href)
                    if len(article_urls) >= limit:
                        break

                tasks = [_fetch_article(client, url, self.source_name) for url in article_urls]
                results = await asyncio.gather(*tasks)
                return [r for r in results if r is not None]
            except Exception as exc:
                logger.warning(f"[BlogScraper] {self.source_name} failed: {exc}")
                return []


async def scrape_all_blogs() -> list[RawArticle]:
    scrapers = [BlogScraper(cfg) for cfg in BLOG_SOURCES]
    results = await asyncio.gather(*[s.scrape() for s in scrapers])
    return [a for batch in results for a in batch]
