import asyncio
import logging
from datetime import datetime, timedelta, timezone

import praw

from app.config import settings
from app.scrapers.base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "ChatGPT",
    "OpenAI",
    "LocalLLaMA",
    "singularity",
    "StableDiffusion",
    "ClaudeAI",
    "Bard",
    "GoogleGemini",
    "AIAssistants",
]

MIN_UPVOTES = 30


class RedditScraper(BaseScraper):
    source_type = "reddit"

    def __init__(self):
        self._reddit: praw.Reddit | None = None

    def _get_reddit(self) -> praw.Reddit:
        if self._reddit is None:
            self._reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
        return self._reddit

    async def _fetch(self) -> list[RawArticle]:
        return await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> list[RawArticle]:
        reddit = self._get_reddit()
        articles: list[RawArticle] = []
        limit = settings.max_articles_per_source
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for sub_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=limit):
                    if post.score < MIN_UPVOTES or post.stickied:
                        continue
                    post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    if post_time < cutoff:
                        continue
                    text = post.selftext or post.title
                    if post.url and not post.is_self:
                        text = f"{post.title}\n\n{post.url}"
                    articles.append(
                        RawArticle(
                            url=f"https://reddit.com{post.permalink}",
                            title=post.title,
                            source_name=f"r/{sub_name}",
                            source_type="reddit",
                            raw_text=text[:4000],
                            published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        )
                    )
            except Exception as exc:
                logger.warning(f"[Reddit] r/{sub_name} failed: {exc}")

        return articles
