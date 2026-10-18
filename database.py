"""MongoDB connection and collection helpers."""

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from config import MONGODB_DATABASE, MONGODB_URI
from models import Article, DailyBriefing

_mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)


def check_connection() -> None:
    """Check MongoDB availability and raise a safe, useful error if offline."""
    try:
        _mongo_client.admin.command("ping")
    except PyMongoError as error:
        raise ConnectionError(
            "Could not connect to MongoDB. Check that MongoDB is running "
            "and MONGODB_URI is correct."
        ) from error


def get_database() -> Database:
    """Return the configured project database."""
    return _mongo_client[MONGODB_DATABASE]


def get_news_collection() -> Collection:
    """Return the collection that stores news articles."""
    return get_database()["news"]


def get_briefings_collection() -> Collection:
    """Return the collection that stores daily briefings."""
    return get_database()["daily_briefings"]


def initialize_database() -> None:
    """Check the connection and create indexes needed by the application."""
    check_connection()
    get_news_collection().create_index("url", unique=True)
    get_briefings_collection().create_index("briefing_date", unique=True)


def save_articles(articles: list[Article]) -> tuple[int, int]:
    """Save articles, returning (inserted count, duplicate count)."""
    inserted_count = 0
    duplicate_count = 0
    collection = get_news_collection()

    for article in articles:
        try:
            collection.insert_one(article)
            inserted_count += 1
        except DuplicateKeyError:
            duplicate_count += 1
        except PyMongoError as error:
            raise RuntimeError(
                "Could not save news to MongoDB. Check the database connection."
            ) from error

    return inserted_count, duplicate_count


def save_briefing(briefing: DailyBriefing) -> None:
    """Insert or replace the briefing for its date."""
    try:
        get_briefings_collection().replace_one(
            {"briefing_date": briefing["briefing_date"]},
            briefing,
            upsert=True,
        )
    except PyMongoError as error:
        raise RuntimeError(
            "Could not save the daily briefing to MongoDB. Check the database connection."
        ) from error
