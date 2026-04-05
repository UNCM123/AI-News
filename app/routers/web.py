import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Article, Digest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")

CATEGORIES = ["Models & Research", "Products & Tools", "Industry News", "Community"]


def _group_by_category(articles) -> dict[str, list]:
    grouped: dict[str, list] = {cat: [] for cat in CATEGORIES}
    for a in articles:
        cat = a.category or "Industry News"
        grouped.setdefault(cat, []).append(a)
    return grouped


async def _get_recent_digests(db: AsyncSession, limit: int = 7) -> list[Digest]:
    result = await db.execute(
        select(Digest).order_by(Digest.date.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Digest)
        .options(selectinload(Digest.articles))
        .order_by(Digest.date.desc())
        .limit(1)
    )
    digest = result.scalar_one_or_none()
    recent_digests = await _get_recent_digests(db)
    articles_by_category = _group_by_category(digest.articles if digest else [])

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "digest": digest,
            "articles_by_category": articles_by_category,
            "categories": CATEGORIES,
            "recent_digests": recent_digests,
            "now": datetime.utcnow(),
        },
    )


@router.get("/digest/{target_date}", response_class=HTMLResponse)
async def digest_by_date(request: Request, target_date: date, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Digest)
        .options(selectinload(Digest.articles))
        .where(Digest.date == target_date)
    )
    digest = result.scalar_one_or_none()
    recent_digests = await _get_recent_digests(db)
    articles_by_category = _group_by_category(digest.articles if digest else [])

    return templates.TemplateResponse(
        "digest.html",
        {
            "request": request,
            "digest": digest,
            "target_date": target_date,
            "articles_by_category": articles_by_category,
            "categories": CATEGORIES,
            "recent_digests": recent_digests,
            "now": datetime.utcnow(),
        },
    )


@router.post("/refresh")
async def refresh(request: Request):
    """Trigger a manual scrape in the background."""
    try:
        import asyncio
        from app.scheduler import run_full_scrape_and_digest

        asyncio.create_task(run_full_scrape_and_digest())
        logger.info("[Web] Manual refresh triggered")
    except Exception as exc:
        logger.warning(f"[Web] refresh trigger failed: {exc}")
    return RedirectResponse(url="/?refreshed=1", status_code=303)
