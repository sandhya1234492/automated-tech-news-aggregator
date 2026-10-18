"""Select important articles and create a readable daily briefing."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from models import Article, DailyBriefing
from news_service import CATEGORY_KEYWORDS

MAX_BRIEFING_ARTICLES = 12
MAX_ARTICLES_PER_SECTION = 2

SECTION_CATEGORIES = {
    "AI": ("AI",),
    "AGENTIC AI": ("Agentic AI",),
    "QUANTUM COMPUTING": ("Quantum Computing",),
    "CLOUD & SOFTWARE": ("Cloud", "Programming", "Developer Tools"),
    "CYBERSECURITY": ("Cybersecurity",),
    "TECHNOLOGY BUSINESS": ("Startups", "Technology Companies"),
}

IMPORTANT_TERMS = (
    "announces",
    "announced",
    "launches",
    "launched",
    "breakthrough",
    "record",
    "major",
    "critical",
    "vulnerability",
    "breach",
    "outage",
    "funding",
    "acquisition",
)

WHY_IT_MATTERS = {
    "AI": "This may influence how AI tools and services are developed or used.",
    "Agentic AI": "This may affect how software agents can carry out tasks autonomously.",
    "Quantum Computing": "This offers a signal about progress toward practical quantum computing.",
    "Cloud": "This may affect how organizations build, operate, or secure cloud services.",
    "Cybersecurity": "This is relevant to protecting systems, data, and users.",
    "Programming": "This may influence the tools and practices developers use.",
    "Developer Tools": "This may change how developers build, test, or maintain software.",
    "Startups": "This provides a signal about investment and opportunities in technology businesses.",
    "Technology Companies": "This may influence products, competition, or strategy across the technology industry.",
}


def score_article(article: Article, now: datetime | None = None) -> int:
    """Give an article a simple score based on topic, impact words, and recency."""
    score = 0
    category = article.get("category")

    if category in CATEGORY_KEYWORDS and category != "Other Technology":
        score += 3

    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    score += sum(2 for term in IMPORTANT_TERMS if term in text)

    current_time = now or datetime.now(timezone.utc)
    published_at = article.get("published_at")
    if isinstance(published_at, datetime):
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age = current_time - published_at
        if timedelta(0) <= age <= timedelta(days=1):
            score += 3
        elif timedelta(0) <= age <= timedelta(days=7):
            score += 1

    return score


def select_top_news(
    articles: list[Article],
    limit: int = MAX_BRIEFING_ARTICLES,
    now: datetime | None = None,
) -> list[Article]:
    """Select highest-scoring articles without repeating a URL."""
    if limit < 0:
        raise ValueError("The article limit cannot be negative.")

    unique_articles: dict[str, Article] = {}
    for article in articles:
        url = article.get("url")
        if not isinstance(url, str) or not url:
            continue
        existing = unique_articles.get(url)
        if existing is None or score_article(article, now) > score_article(existing, now):
            unique_articles[url] = article

    return sorted(
        unique_articles.values(),
        key=lambda article: (
            score_article(article, now),
            article.get("published_at")
            if isinstance(article.get("published_at"), datetime)
            else datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )[:limit]


def _summary(article: Article) -> str:
    description = article.get("description")
    if not isinstance(description, str) or not description.strip():
        return "No summary was provided by the news source."
    return description.strip()


def _learning_topic(category_counts: Counter[str]) -> str:
    if not category_counts:
        return "Review the fundamentals of reading and evaluating technology news."

    most_covered = category_counts.most_common(1)[0][0]
    topics = {
        "AI": "Study how large language models are trained, evaluated, and used.",
        "Agentic AI": "Learn how tool-calling AI agents plan tasks and handle failures.",
        "Quantum Computing": "Review qubits, quantum gates, and the limits of current hardware.",
        "Cloud": "Practice deploying a small application and monitoring its cloud resources.",
        "Cybersecurity": "Learn the basics of threat modeling and multi-factor authentication.",
        "Programming": "Practice writing tests and using version control in a small project.",
        "Developer Tools": "Explore how a modern IDE supports testing, debugging, and code review.",
        "Startups": "Learn how technology startups validate a product and measure traction.",
        "Technology Companies": "Compare how major technology companies compete in a shared market.",
    }
    return topics.get(most_covered, "Practice checking a technology story against its original source.")


def _career_opportunity(category_counts: Counter[str]) -> str:
    if not category_counts:
        return "Follow technology job postings and build a small project to demonstrate practical skills."

    most_covered = category_counts.most_common(1)[0][0]
    opportunities = {
        "AI": "Explore Python, data skills, and AI evaluation for junior AI or data roles.",
        "Agentic AI": "Practice Python APIs and tool integration for AI application development.",
        "Quantum Computing": "Build foundations in linear algebra and quantum programming tools.",
        "Cloud": "Practice cloud fundamentals, Linux, and deployment for cloud support roles.",
        "Cybersecurity": "Build networking and security fundamentals for entry-level security roles.",
        "Programming": "Strengthen programming, testing, and Git skills for junior developer roles.",
        "Developer Tools": "Learn build, test, and debugging workflows used by software teams.",
        "Startups": "Develop product, communication, and data-analysis skills valued by small teams.",
        "Technology Companies": "Follow the tools and platforms used in roles at major technology firms.",
    }
    return opportunities.get(most_covered, "Build practical programming skills and track relevant entry-level roles.")


def generate_briefing(
    articles: list[Article],
    briefing_date: date | None = None,
    generated_at: datetime | None = None,
) -> DailyBriefing:
    """Create a briefing document and printable text from collected articles."""
    today = briefing_date or date.today()
    created_time = generated_at or datetime.now(timezone.utc)
    top_news = select_top_news(articles)
    category_counts = Counter(
        article["category"]
        for article in top_news
        if isinstance(article.get("category"), str)
    )

    sections: dict[str, list[Article]] = {}
    for section, categories in SECTION_CATEGORIES.items():
        matches = [article for article in top_news if article.get("category") in categories]
        sections[section] = matches[:MAX_ARTICLES_PER_SECTION]

    lines = [
        "DAILY GLOBAL TECH BRIEFING",
        f"Date: {today.isoformat()}",
        "",
    ]
    for section, section_articles in sections.items():
        lines.append(section)
        if not section_articles:
            lines.append("- No matching stories were collected today.")
        for article in section_articles:
            lines.extend(
                [
                    f"- {article['title']}",
                    f"  Summary: {_summary(article)}",
                    f"  Why it matters: {WHY_IT_MATTERS.get(article.get('category'), 'This is a technology development worth following.')}",
                    f"  Source: {article.get('source') or 'Unknown'}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "LEARNING OF THE DAY",
            _learning_topic(category_counts),
            "",
            "CAREER OPPORTUNITY",
            _career_opportunity(category_counts),
        ]
    )
    text = "\n".join(lines)

    return {
        "briefing_date": today.isoformat(),
        "generated_at": created_time,
        "total_news": len(top_news),
        "categories": dict(category_counts),
        "top_news": top_news,
        "text": text,
        "created_at": created_time,
    }
