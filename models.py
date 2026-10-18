"""Simple type definitions for articles and daily briefing documents."""

from datetime import datetime
from typing import TypedDict


class Article(TypedDict):
    """Fields stored for one news article."""

    title: str
    description: str
    source: str
    author: str | None
    url: str
    category: str
    published_at: datetime | None
    collected_at: datetime


class DailyBriefing(TypedDict):
    """Fields stored for one daily briefing."""

    briefing_date: str
    generated_at: datetime
    total_news: int
    categories: dict[str, int]
    top_news: list[Article]
    text: str
    created_at: datetime
