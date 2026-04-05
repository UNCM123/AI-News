from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class ArticleOut(BaseModel):
    id: int
    url: str
    title: str
    source_name: str
    source_type: str
    category: Optional[str]
    summary: Optional[str]
    published_at: Optional[datetime]
    scraped_at: datetime

    model_config = {"from_attributes": True}


class DigestOut(BaseModel):
    id: int
    date: date
    headline_summary: Optional[str]
    article_count: int
    generated_at: datetime
    articles: List[ArticleOut] = []

    model_config = {"from_attributes": True}


class DigestSummary(BaseModel):
    id: int
    date: date
    article_count: int
    generated_at: datetime

    model_config = {"from_attributes": True}
