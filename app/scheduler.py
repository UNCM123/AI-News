import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_full_scrape_and_digest() -> None:
    """Main job: scrape all sources, summarize new articles, build digest."""
    logger.info("[Scheduler] Starting scrape cycle...")
    start = datetime.utcnow()

    from app.scrapers.blog_scraper import scrape_all_blogs
    from app.scrapers.reddit_scraper import RedditScraper
    from app.scrapers.rss_scraper import scrape_all_rss
    from app.scrapers.twitter_scraper import scrape_all_twitter
    from app.database import AsyncSessionLocal
    from app.digest_builder import build_or_update_digest, save_articles

    # Run all scrapers concurrently
    reddit_scraper = RedditScraper()
    rss_task = scrape_all_rss()
    blog_task = scrape_all_blogs()
    twitter_task = scrape_all_twitter()
    reddit_task = reddit_scraper.scrape()

    results = await asyncio.gather(rss_task, blog_task, twitter_task, reddit_task, return_exceptions=True)

    all_articles = []
    source_names = ["RSS", "Blogs", "Twitter", "Reddit"]
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            logger.warning(f"[Scheduler] {name} scraper raised: {result}")
        else:
            all_articles.extend(result)
            logger.info(f"[Scheduler] {name}: {len(result)} articles")

    logger.info(f"[Scheduler] Total raw articles: {len(all_articles)}")

    # Persist and build digest
    async with AsyncSessionLocal() as db:
        await save_articles(db, all_articles)
        await build_or_update_digest(db)

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info(f"[Scheduler] Scrape cycle complete in {elapsed:.1f}s")


async def start_scheduler() -> None:
    scheduler.add_job(
        run_full_scrape_and_digest,
        trigger="interval",
        hours=settings.scrape_interval_hours,
        next_run_time=datetime.now(),
        id="scrape_and_digest",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()


async def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
