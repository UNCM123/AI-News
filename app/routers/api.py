from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Article, Digest
from app.schemas import ArticleOut, DigestOut, DigestSummary

router = APIRouter(tags=["api"])


@router.get("/digest/latest", response_model=DigestOut)
async def get_latest_digest(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Digest)
        .options(selectinload(Digest.articles))
        .order_by(Digest.date.desc())
        .limit(1)
    )
    digest = result.scalar_one_or_none()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest found")
    return digest


@router.get("/digest/{target_date}", response_model=DigestOut)
async def get_digest_by_date(target_date: date, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Digest)
        .options(selectinload(Digest.articles))
        .where(Digest.date == target_date)
    )
    digest = result.scalar_one_or_none()
    if not digest:
        raise HTTPException(status_code=404, detail=f"No digest for {target_date}")
    return digest


@router.get("/digests", response_model=list[DigestSummary])
async def list_digests(limit: int = Query(30, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Digest).order_by(Digest.date.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/articles", response_model=list[ArticleOut])
async def list_articles(
    source: str | None = None,
    category: str | None = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Article).order_by(Article.scraped_at.desc())
    if source:
        q = q.where(Article.source_name.ilike(f"%{source}%"))
    if category:
        q = q.where(Article.category == category)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
