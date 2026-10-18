"""Load shared application settings from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_NEWS_API_URL = "https://newsapi.org/v2/everything"

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "tech_news")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = os.getenv("NEWS_API_URL", "").strip() or DEFAULT_NEWS_API_URL

NEWS_SCHEDULE_HOUR = int(os.getenv("NEWS_SCHEDULE_HOUR", "6"))
NEWS_SCHEDULE_MINUTE = int(os.getenv("NEWS_SCHEDULE_MINUTE", "0"))

if not 0 <= NEWS_SCHEDULE_HOUR <= 23:
    raise ValueError("NEWS_SCHEDULE_HOUR must be between 0 and 23.")

if not 0 <= NEWS_SCHEDULE_MINUTE <= 59:
    raise ValueError("NEWS_SCHEDULE_MINUTE must be between 0 and 59.")
