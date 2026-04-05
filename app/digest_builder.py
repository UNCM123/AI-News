import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Digest
from app.scrapers.base import RawArticle
from app.summarizer import generate_digest_summary, summarize_article

logger = logging.getLogger(__name__)


async def get_existing_urls(db: AsyncSession) -> Set[str]:
    result = await db.execute(select(Article.url))
    return {row[0] for row in result.fetchall()}


async def save_articles(db: AsyncSession, raw_articles: List[RawArticle]) -> List[Article]:
    """Deduplicate, summarize, and persist new articles. Returns saved articles."""
    existing_urls = await get_existing_urls(db)

    # Also deduplicate within this batch itself (multiple scrapers may find same URL)
    seen_in_batch: Set[str] = set()
    new_raw = []
    for a in raw_articles:
        if a.url not in existing_urls and a.url not in seen_in_batch:
            seen_in_batch.add(a.url)
            new_raw.append(a)

    logger.info(f"[Digest] {len(raw_articles)} scraped, {len(new_raw)} new after dedup")

    saved: List[Article] = []
    for raw in new_raw:
        text = raw.raw_text or raw.title
        summary, category = await summarize_article(raw.title, text, raw.source_name)
        article = Article(
            url=raw.url,
            title=raw.title,
            source_name=raw.source_name,
            source_type=raw.source_type,
            category=category,
            raw_text=raw.raw_text,
            summary=summary,
            published_at=raw.published_at,
            scraped_at=datetime.utcnow(),
        )
        try:
            db.add(article)
            await db.commit()
            await db.refresh(article)
            saved.append(article)
        except IntegrityError:
            await db.rollback()
            logger.debug(f"[Digest] skipped duplicate: {raw.url}")

    logger.info(f"[Digest] saved {len(saved)} new articles")
    return saved


async def build_or_update_digest(db: AsyncSession, target_date: Optional[date] = None) -> Digest:
    """Create or update today's digest with all articles from today."""
    if target_date is None:
        target_date = date.today()

    # Load or create digest
    result = await db.execute(select(Digest).where(Digest.date == target_date))
    digest = result.scalar_one_or_none()
    if digest is None:
        digest = Digest(date=target_date)
        db.add(digest)

    # Fetch articles from the last 24 hours
    # Use published_at if available, fall back to scraped_at for blogs without dates
    cutoff = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(Article).where(
            or_(
                Article.published_at >= cutoff,
                and_(Article.published_at == None, Article.scraped_at >= cutoff),
            )
        )
    )
    articles = result.scalars().all()

    # Assign articles to this digest
    for article in articles:
        article.digest_id = digest.id if digest.id else None

    # Group by category for summary generation
    by_category: Dict[str, list] = {}
    for article in articles:
        cat = article.category or "Industry News"
        by_category.setdefault(cat, []).append(article)

    digest.headline_summary = await generate_digest_summary(by_category)
    digest.article_count = len(articles)
    digest.generated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(digest)

    # Re-assign digest_id now that we have digest.id
    for article in articles:
        if article.digest_id != digest.id:
            article.digest_id = digest.id
    await db.commit()

    logger.info(f"[Digest] built digest for {target_date}: {len(articles)} articles")
    return digest
