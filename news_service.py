"""Fetch and categorize news articles from NewsAPI.org."""

import re
from datetime import datetime, timezone
from typing import Any

import requests

from config import NEWS_API_KEY, NEWS_API_URL
from models import Article

REQUEST_TIMEOUT_SECONDS = 10
NEWS_QUERY = (
    '"artificial intelligence" OR "agentic AI" OR quantum OR '
    '"cloud computing" OR cybersecurity OR programming OR '
    '"developer tools" OR startup OR technology'
)

CATEGORY_KEYWORDS = {
    "Agentic AI": ("agentic ai", "ai agent", "ai agents", "autonomous agent"),
    "Quantum Computing": ("quantum", "qubit"),
    "AI": ("artificial intelligence", "machine learning", "generative ai"),
    "Cloud": ("cloud computing", "cloud service", "cloud platform"),
    "Cybersecurity": ("cybersecurity", "cyber attack", "data breach", "ransomware"),
    "Programming": ("programming", "programming language", "python", "javascript"),
    "Developer Tools": (
        "developer tool",
        "software architecture",
        "software development",
        "github",
        "ide",
    ),
    "Startups": ("startup", "venture capital", "funding round"),
    "Technology Companies": (
        "technology company",
        "tech company",
        "apple",
        "google",
        "microsoft",
        "amazon",
        "nvidia",
    ),
}


def categorize_article(title: str, description: str) -> str:
    """Choose the first matching category from the editable keyword lists."""
    text = f"{title} {description}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
            if re.search(pattern, text):
                return category

    return "Other Technology"


def _parse_published_at(value: Any) -> datetime | None:
    """Convert an ISO-formatted publication date to a timezone-aware datetime."""
    if not isinstance(value, str):
        return None

    try:
        published_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if published_at.tzinfo is None:
        return published_at.replace(tzinfo=timezone.utc)
    return published_at


def _prepare_article(article: Any) -> Article | None:
    """Extract the fields used by the project from one NewsAPI article."""
    if not isinstance(article, dict):
        return None

    title = article.get("title")
    url = article.get("url")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(url, str) or not url.strip():
        return None

    description = article.get("description")
    if not isinstance(description, str):
        description = ""

    source = article.get("source")
    source_name = source.get("name") if isinstance(source, dict) else None

    author = article.get("author")
    if not isinstance(author, str) or not author.strip():
        author = None

    return {
        "title": title.strip(),
        "description": description.strip(),
        "source": source_name if isinstance(source_name, str) else "Unknown",
        "author": author,
        "published_at": _parse_published_at(article.get("publishedAt")),
        "url": url.strip(),
        "category": categorize_article(title, description),
        "collected_at": datetime.now(timezone.utc),
    }


def fetch_news() -> list[Article]:
    """Fetch the latest technology news and return prepared article dictionaries."""
    if not NEWS_API_KEY:
        raise RuntimeError(
            "NEWS_API_KEY is missing. Add your NewsAPI.org key to the local .env file."
        )

    try:
        response = requests.get(
            NEWS_API_URL,
            params={
                "q": NEWS_QUERY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 100,
            },
            headers={"X-Api-Key": NEWS_API_KEY},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as error:
        raise RuntimeError("The news request timed out. Please try again later.") from error
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else None
        if status_code == 401:
            message = (
                "NewsAPI.org rejected the API key. Copy a valid key from your "
                "NewsAPI.org account into NEWS_API_KEY in .env."
            )
        elif status_code == 429:
            message = "NewsAPI.org rate limit reached. Wait before trying again."
        elif status_code == 403:
            message = (
                "NewsAPI.org denied this request. Check your account access "
                "and plan limits."
            )
        else:
            message = (
                "NewsAPI.org returned an HTTP error. Check the provider status "
                "and your account settings."
            )
        raise RuntimeError(message) from error
    except requests.RequestException as error:
        raise RuntimeError(
            "The news request failed. Check the NewsAPI URL, API key, and service status."
        ) from error

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("The news provider returned invalid JSON.") from error

    if not isinstance(payload, dict):
        raise RuntimeError("The news provider returned an unexpected response.")
    if payload.get("status") != "ok":
        raise RuntimeError(
            "The news provider rejected the request. Check the API key and account limits."
        )

    articles = payload.get("articles")
    if not isinstance(articles, list):
        raise RuntimeError("The news provider response did not contain an article list.")

    prepared_articles: list[Article] = []
    for article in articles:
        prepared_article = _prepare_article(article)
        if prepared_article is not None:
            prepared_articles.append(prepared_article)

    return prepared_articles
