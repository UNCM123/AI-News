from datetime import date, datetime

from pydantic import BaseModel


class ArticleOut(BaseModel):
    id: int
    url: str
    title: str
    source_name: str
    source_type: str
    category: str | None
    summary: str | None
    published_at: datetime | None
    scraped_at: datetime

    model_config = {"from_attributes": True}


class DigestOut(BaseModel):
    id: int
    date: date
    headline_summary: str | None
    article_count: int
    generated_at: datetime
    articles: list[ArticleOut] = []

    model_config = {"from_attributes": True}


class DigestSummary(BaseModel):
    id: int
    date: date
    article_count: int
    generated_at: datetime

    model_config = {"from_attributes": True}
