"""Run the daily news collection and briefing job."""

import logging
import sys
from datetime import date, datetime, timezone
from threading import Lock
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from briefing_service import generate_briefing
from config import NEWS_SCHEDULE_HOUR, NEWS_SCHEDULE_MINUTE
from database import initialize_database, save_articles, save_briefing
from models import DailyBriefing
from news_service import fetch_news

logger = logging.getLogger(__name__)

INTERVAL_OPTIONS = {
    "1m": {"label": "Every 1 minute", "seconds": 60},
    "5m": {"label": "Every 5 minutes", "seconds": 5 * 60},
    "1h": {"label": "Every 1 hour", "seconds": 60 * 60},
    "1d": {"label": "Every 1 day", "seconds": 24 * 60 * 60},
}

_interval_scheduler = BackgroundScheduler()
_scheduler_lock = Lock()
_last_started: datetime | None = None
_last_completed: datetime | None = None
_last_error: str | None = None
_active_interval: str | None = None


def run_daily_job() -> DailyBriefing:
    """Fetch news, store articles and a briefing, then print the briefing."""
    initialize_database()
    articles = fetch_news()
    inserted_count, duplicate_count = save_articles(articles)
    briefing = generate_briefing(articles, briefing_date=date.today())
    save_briefing(briefing)

    print(
        f"News collected: {len(articles)}; newly stored: {inserted_count}; "
        f"duplicates skipped: {duplicate_count}"
    )
    try:
        print(briefing["text"])
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_text = briefing["text"].encode(
            encoding,
            errors="backslashreplace",
        ).decode(encoding)
        print(safe_text)
    return briefing


def _run_scheduled_job() -> None:
    """Run one interval job and retain a safe status for the dashboard."""
    global _last_started, _last_completed, _last_error

    with _scheduler_lock:
        _last_started = datetime.now(timezone.utc)
        _last_error = None

    try:
        run_daily_job()
    except Exception:
        logger.exception("Scheduled news collection failed.")
        with _scheduler_lock:
            _last_error = "The last scheduled collection failed. Check the server terminal."
    finally:
        with _scheduler_lock:
            _last_completed = datetime.now(timezone.utc)


def start_interval_scheduler(interval: str) -> dict[str, Any]:
    """Start or update the dashboard-controlled repeating news schedule."""
    global _active_interval

    option = INTERVAL_OPTIONS.get(interval)
    if option is None:
        raise ValueError("Choose one of the supported scheduler intervals.")

    _interval_scheduler.add_job(
        _run_scheduled_job,
        trigger="interval",
        seconds=option["seconds"],
        id="dashboard_news_refresh",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
        max_instances=1,
        coalesce=True,
    )
    with _scheduler_lock:
        _active_interval = interval

    if not _interval_scheduler.running:
        _interval_scheduler.start()

    return get_interval_scheduler_status()


def stop_interval_scheduler() -> dict[str, Any]:
    """Stop the repeating schedule selected in the dashboard."""
    global _active_interval

    if _interval_scheduler.running:
        job = _interval_scheduler.get_job("dashboard_news_refresh")
        if job is not None:
            _interval_scheduler.remove_job("dashboard_news_refresh")
    with _scheduler_lock:
        _active_interval = None

    return get_interval_scheduler_status()


def get_interval_scheduler_status() -> dict[str, Any]:
    """Return dashboard-safe scheduler status and the latest run timestamps."""
    job = _interval_scheduler.get_job("dashboard_news_refresh")
    with _scheduler_lock:
        return {
            "running": job is not None and _interval_scheduler.running,
            "interval": _active_interval,
            "interval_label": (
                INTERVAL_OPTIONS[_active_interval]["label"]
                if _active_interval is not None
                else None
            ),
            "next_run_time": job.next_run_time if job is not None else None,
            "last_started": _last_started,
            "last_completed": _last_completed,
            "last_error": _last_error,
        }


def start_scheduler() -> None:
    """Run the daily job every day at the configured local time."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_daily_job,
        trigger="cron",
        hour=NEWS_SCHEDULE_HOUR,
        minute=NEWS_SCHEDULE_MINUTE,
        id="daily_news_briefing",
        replace_existing=True,
    )
    print(
        "Daily news scheduler started. "
        f"The job will run at {NEWS_SCHEDULE_HOUR:02d}:{NEWS_SCHEDULE_MINUTE:02d} local time."
    )
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
