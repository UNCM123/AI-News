from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class Digest(Base):
    __tablename__ = "digests"

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    headline_summary = Column(Text)
    article_count = Column(Integer, default=0)
    generated_at = Column(DateTime, default=func.now())

    articles = relationship("Article", back_populates="digest")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    url = Column(String(2048), unique=True, nullable=False)
    title = Column(String(512), nullable=False)
    source_name = Column(String(128), nullable=False)
    source_type = Column(String(32), nullable=False)
    category = Column(String(64))
    raw_text = Column(Text)
    summary = Column(Text)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=func.now())
    digest_id = Column(Integer, ForeignKey("digests.id"), nullable=True)

    digest = relationship("Digest", back_populates="articles")
