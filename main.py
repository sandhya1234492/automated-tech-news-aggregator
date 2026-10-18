"""Simple REST API for stored technology news and briefings."""

import re
from datetime import date, datetime
from typing import Any

from bson import ObjectId
from flask import Flask, jsonify, render_template, request
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from database import (
    check_connection,
    get_briefings_collection,
    get_news_collection,
)
from news_service import CATEGORY_KEYWORDS
from scheduler import (
    INTERVAL_OPTIONS,
    get_interval_scheduler_status,
    start_interval_scheduler,
    stop_interval_scheduler,
)

app = Flask(__name__)

VALID_CATEGORIES = {
    category.casefold(): category
    for category in (*CATEGORY_KEYWORDS.keys(), "Other Technology")
}
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _to_json_value(value: Any) -> Any:
    """Convert MongoDB values into types Flask can return as JSON."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    return value


def _error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def _get_page_size() -> tuple[int | None, tuple[Any, int] | None]:
    raw_limit = request.args.get("limit")
    if raw_limit is None:
        return DEFAULT_PAGE_SIZE, None

    try:
        limit = int(raw_limit)
    except ValueError:
        return None, _error("The limit must be a whole number.", 400)

    if not 1 <= limit <= MAX_PAGE_SIZE:
        return None, _error(f"The limit must be between 1 and {MAX_PAGE_SIZE}.", 400)
    return limit, None


@app.errorhandler(PyMongoError)
def handle_database_error(_error_value: PyMongoError):
    """Return a safe response when a MongoDB operation fails."""
    return _error("The database request could not be completed.", 503)


@app.get("/")
def home():
    """Show the browser dashboard for trying the API."""
    return render_template("index.html", categories=sorted(VALID_CATEGORIES.values()))


@app.get("/health")
def health():
    """Report whether the API process and MongoDB are available."""
    try:
        check_connection()
    except ConnectionError:
        return jsonify({"status": "error", "database": "unavailable"}), 503
    return jsonify({"status": "ok", "database": "connected"}), 200


@app.get("/scheduler/status")
def scheduler_status():
    """Return the interval scheduler state for the browser dashboard."""
    status = get_interval_scheduler_status()
    status["intervals"] = {
        key: {"label": value["label"], "seconds": value["seconds"]}
        for key, value in INTERVAL_OPTIONS.items()
    }
    return jsonify(_to_json_value(status)), 200


@app.post("/scheduler/start")
def scheduler_start():
    """Start the dashboard's recurring job at a supported interval."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error("Send a JSON object containing an interval.", 400)

    interval = payload.get("interval")
    if not isinstance(interval, str):
        return _error("Choose a supported scheduler interval.", 400)

    try:
        status = start_interval_scheduler(interval)
    except ValueError as error:
        return _error(str(error), 400)
    return jsonify(_to_json_value(status)), 200


@app.post("/scheduler/stop")
def scheduler_stop():
    """Stop the dashboard's recurring collection job."""
    return jsonify(_to_json_value(stop_interval_scheduler())), 200


@app.get("/news")
def latest_news():
    """Return the newest stored articles."""
    limit, error_response = _get_page_size()
    if error_response:
        return error_response

    articles = list(
        get_news_collection()
        .find()
        .sort("published_at", DESCENDING)
        .limit(limit)
    )
    return jsonify({"items": _to_json_value(articles), "count": len(articles)}), 200


@app.get("/news/search")
def search_news():
    """Search article titles, descriptions, and categories."""
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return _error("The keyword query parameter is required.", 400)

    limit, error_response = _get_page_size()
    if error_response:
        return error_response

    escaped_keyword = re.escape(keyword)
    query = {
        "$or": [
            {"title": {"$regex": escaped_keyword, "$options": "i"}},
            {"description": {"$regex": escaped_keyword, "$options": "i"}},
            {"category": {"$regex": escaped_keyword, "$options": "i"}},
        ]
    }
    articles = list(
        get_news_collection()
        .find(query)
        .sort("published_at", DESCENDING)
        .limit(limit)
    )
    return jsonify({"items": _to_json_value(articles), "count": len(articles)}), 200


@app.get("/news/category/<category>")
def news_by_category(category: str):
    """Return articles for one of the project's supported categories."""
    canonical_category = VALID_CATEGORIES.get(category.casefold())
    if canonical_category is None:
        return _error("Unknown news category.", 400)

    limit, error_response = _get_page_size()
    if error_response:
        return error_response

    articles = list(
        get_news_collection()
        .find({"category": canonical_category})
        .sort("published_at", DESCENDING)
        .limit(limit)
    )
    return jsonify({"items": _to_json_value(articles), "count": len(articles)}), 200


@app.get("/news/<article_id>")
def news_by_id(article_id: str):
    """Return one article by its MongoDB ObjectId."""
    if not ObjectId.is_valid(article_id):
        return _error("The article ID is invalid.", 400)

    article = get_news_collection().find_one({"_id": ObjectId(article_id)})
    if article is None:
        return _error("Article not found.", 404)
    return jsonify(_to_json_value(article)), 200


@app.get("/briefings")
def previous_briefings():
    """Return recent daily briefings."""
    limit, error_response = _get_page_size()
    if error_response:
        return error_response

    briefings = list(
        get_briefings_collection()
        .find()
        .sort("briefing_date", DESCENDING)
        .limit(limit)
    )
    return jsonify({"items": _to_json_value(briefings), "count": len(briefings)}), 200


@app.get("/briefings/<briefing_date>")
def briefing_by_date(briefing_date: str):
    """Return the briefing for a date formatted as YYYY-MM-DD."""
    try:
        parsed_date = date.fromisoformat(briefing_date)
    except ValueError:
        return _error("The date must use YYYY-MM-DD format.", 400)
    if parsed_date.isoformat() != briefing_date:
        return _error("The date must use YYYY-MM-DD format.", 400)

    briefing = get_briefings_collection().find_one(
        {"briefing_date": parsed_date.isoformat()}
    )
    if briefing is None:
        return _error("Briefing not found.", 404)
    return jsonify(_to_json_value(briefing)), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
