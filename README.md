# Daily Global Tech News Scheduler

A beginner-friendly Python application that collects technology news from
NewsAPI.org, stores articles in MongoDB, and creates a daily technology
briefing. It also provides a small REST API for browsing, filtering, and
searching saved news.

This project uses keyword rules and a transparent scoring heuristic. It does
not use an AI model to write or verify article summaries: summaries come from
the news source descriptions.

## Technologies

- Python
- MongoDB and PyMongo
- NewsAPI.org JSON API and Requests
- Flask REST API
- APScheduler
- VS Code and Postman

## Project files

| File | Purpose |
|---|---|
| `main.py` | REST API routes for health, news, search, and briefings |
| `config.py` | Reads database, news provider, and schedule settings |
| `database.py` | MongoDB connection, indexes, and storage functions |
| `news_service.py` | Fetches, parses, and categorizes NewsAPI articles |
| `briefing_service.py` | Scores articles and builds briefing text |
| `scheduler.py` | Runs the daily collection and briefing job |
| `models.py` | Documents the article and briefing data fields |
| `.env.example` | Safe template for local environment settings |
| `requirements.txt` | Python packages used by the application |

## Installation

Use Python 3.10 or newer. In a VS Code terminal opened at the project folder,
create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual environment activation, use the environment's
Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## MongoDB setup

Install and start MongoDB Community Server locally, or create a MongoDB Atlas
cluster. For a local MongoDB server, the default connection string is
`mongodb://localhost:27017`. For Atlas, copy the connection string from Atlas
and replace its username, password, and database placeholders in your local
`.env` file. Never share or commit a connection string containing a password.

MongoDB Compass is optional but useful for inspecting the stored documents.
Connect Compass with the same URI as `MONGODB_URI`. After the first successful
application run, open the `tech_news` database and inspect `news` and
`daily_briefings`.

## Environment variables

Copy `.env.example` to `.env` and set your own NewsAPI.org key. In PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally. `NEWS_API_KEY` is required for collection. The NewsAPI.org
free plan may have usage and availability limits; check the provider's current
terms for your account.

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `MONGODB_URI` | No | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | No | `tech_news` | Database name |
| `NEWS_API_KEY` | Yes for fetching | Empty | NewsAPI.org API key |
| `NEWS_API_URL` | No | NewsAPI.org `/v2/everything` endpoint | News API endpoint |
| `NEWS_SCHEDULE_HOUR` | No | `6` | Daily run hour, 0–23 local time |
| `NEWS_SCHEDULE_MINUTE` | No | `0` | Daily run minute, 0–59 |

`.env` and other `.env.*` files are ignored by Git; `.env.example` is
intentionally kept in version control and contains no credentials.
If `NEWS_API_URL` is omitted or left blank, the application uses the default
NewsAPI.org endpoint.

## Run the application

### Run collection and create today's briefing once

With MongoDB running and `.env` configured:

```powershell
python -c "from scheduler import run_daily_job; run_daily_job()"
```

The job checks the database connection, creates indexes, fetches news, stores
new articles, creates or replaces today's briefing, stores it, and prints it.

### Run the daily scheduler

```powershell
python scheduler.py
```

The scheduler waits for the next configured local time (6:00 AM by default);
it does not run immediately at startup. Keep the terminal and computer running
for the scheduled job to execute. Stop it with `Ctrl+C`.

### Run the REST API

In a separate terminal:

```powershell
python main.py
```

The API listens at `http://127.0.0.1:5000`. Keep the API and scheduler in
separate terminals if you want both to run at the same time.

## How news is categorized and selected

`news_service.py` contains editable keyword lists in `CATEGORY_KEYWORDS`.
Categories are checked in order, so more specific Agentic AI keywords are
checked before general AI keywords. Articles without a match become
`Other Technology`.

`briefing_service.py` assigns a simple score:

- +3 for a recognized technology category.
- +2 for each configured important term in the title or description (for
  example, “launches”, “breakthrough”, “breach”, or “acquisition”).
- +3 if published within the last day, or +1 if published within the last
  seven days.

The highest-scoring articles are considered first, newer publication dates
break ties, and repeated URLs are removed. Up to two articles appear in each
briefing section. Scores are only a transparent rule of thumb, not a guarantee
that the selected news is objectively the most important.

## MongoDB collections

The application uses the database `tech_news` and these collections:

### `news`

One document per article. MongoDB adds `_id` automatically.

```json
{
  "title": "Example technology headline",
  "description": "A short description from the news source.",
  "source": "Example News",
  "author": null,
  "url": "https://example.com/technology-story",
  "category": "AI",
  "published_at": "2026-10-18T05:00:00+00:00",
  "collected_at": "2026-10-18T06:00:00+00:00"
}
```

The unique index on `url` prevents the same article URL from being inserted
more than once.

### `daily_briefings`

One document per briefing date. The date is stored as `YYYY-MM-DD`.

```json
{
  "briefing_date": "2026-10-18",
  "generated_at": "2026-10-18T06:00:00+00:00",
  "total_news": 1,
  "categories": {"AI": 1},
  "top_news": [],
  "text": "DAILY GLOBAL TECH BRIEFING\\nDate: 2026-10-18",
  "created_at": "2026-10-18T06:00:00+00:00"
}
```

The unique index on `briefing_date` and an upsert ensure rerunning the job
replaces that date's briefing rather than adding another copy.

## REST API

Start the API with `python main.py` and open `http://127.0.0.1:5000/` for the
browser dashboard. It can check the API/database connection, list latest
articles, search, filter by category, and load a briefing by date. This UI calls
the same REST endpoints documented below; Postman can still be used to inspect
the raw JSON responses.

List endpoints return newest results first. They accept an optional `limit`
from 1 to 100; the default is 50.

| Method and path | Purpose |
|---|---|
| `GET /health` | Check that the API and MongoDB are available |
| `GET /scheduler/status` | See the dashboard-controlled interval schedule |
| `POST /scheduler/start` | Start repeating collection with a supported interval |
| `POST /scheduler/stop` | Stop the dashboard-controlled interval schedule |
| `GET /news` | Return latest news |
| `GET /news/<id>` | Return one article by MongoDB ObjectId |
| `GET /news/category/<category>` | Filter by a supported category |
| `GET /news/search?keyword=python` | Search title, description, and category |
| `GET /briefings` | Return previous daily briefings |
| `GET /briefings/YYYY-MM-DD` | Return one briefing for a date |

Try these in Postman after starting `main.py`:

```text
GET http://127.0.0.1:5000/health
GET http://127.0.0.1:5000/news?limit=10
GET http://127.0.0.1:5000/news/search?keyword=python
GET http://127.0.0.1:5000/news/category/Quantum%20Computing
GET http://127.0.0.1:5000/briefings
GET http://127.0.0.1:5000/briefings/2026-10-18
```

Example successful list response:

```json
{
  "items": [
    {
      "_id": "6711c2d3e4f5061728394050",
      "title": "Example technology headline",
      "description": "A short description.",
      "source": "Example News",
      "author": null,
      "url": "https://example.com/technology-story",
      "category": "AI",
      "published_at": "2026-10-18T05:00:00+00:00",
      "collected_at": "2026-10-18T06:00:00+00:00"
    }
  ],
  "count": 1
}
```

Example error response when a search keyword is missing:

```json
{"error": "The keyword query parameter is required."}
```

The API returns HTTP 400 for invalid IDs, categories, dates, or limits; 404
when an article or briefing does not exist; and 503 when MongoDB is
unavailable. Internal database details and credentials are not returned.

### Dashboard-controlled refresh schedule

In the dashboard, choose **1 minute**, **5 minutes**, **1 hour**, or **1 day**,
then select **Start auto refresh**. It runs one collection immediately and
repeats at that interval. While the dashboard remains open, it checks schedule
status and reloads the displayed articles and briefing after a run finishes.
Choose **Stop** to cancel future runs. Keep Flask running; the schedule is
held in application memory and stops when the app exits.

The one-minute option is intended for a short test. It makes up to 1,440
provider requests in a day, so it can exceed NewsAPI.org account limits.
Provider limits still apply for every interval.
Use either the dashboard-controlled interval schedule or `python scheduler.py`
for the daily 6:00 AM schedule, not both at the same time, to avoid duplicate
provider requests.

## Request and data flow

```text
NewsAPI.org
    -> news_service.py parses JSON and categorizes articles
    -> database.py stores unique article URLs in MongoDB
    -> briefing_service.py scores and formats selected articles
    -> database.py saves one briefing for the date
    -> scheduler.py prints the briefing and repeats the job daily

Postman/browser
    -> main.py validates the request
    -> database.py queries MongoDB
    -> main.py returns JSON
```

## Troubleshooting

- **MongoDB connection error:** Start MongoDB and check `MONGODB_URI`.
- **Missing news key:** Set `NEWS_API_KEY` in `.env`, not in Python source.
- **News provider error:** Check the API key, account limits, endpoint, and
  network connection.
- **No articles:** A successful empty provider response is allowed; the daily
  briefing will say that no matching stories were collected.
- **Duplicate URL:** MongoDB's unique index rejects repeated article URLs; the
  application counts these as skipped duplicates.
- **Scheduler did not run immediately:** It waits for the next configured
  local time. Keep the scheduler process running.
- **Some briefing characters are not displayed in a Windows terminal:** The
  saved briefing and browser UI retain the original text; characters the
  terminal cannot encode are printed as escape sequences.
- **Postman returns 503:** Confirm MongoDB is running and reachable.

## Learning and demonstration checklist

1. Start MongoDB and run the one-time job.
2. Inspect `news` and `daily_briefings` in MongoDB Compass.
3. Start the REST API and try each endpoint in Postman.
4. Search by a word and filter by a category.
5. Open `http://127.0.0.1:5000/` and test the browser dashboard.
6. Start the scheduler and explain its configured run time.
7. Trace the data from NewsAPI.org through MongoDB to the briefing and API.

Explain each module in your own words and try changing a category keyword or
the scheduler time to demonstrate your understanding.

## Interview questions and detailed answers

### 1. Explain the complete project flow.

The project has two ways to start work:

- A person can run `run_daily_job()` once from the terminal.
- The scheduler can call the same job automatically at its configured time or
  interval.

The job first checks that MongoDB is available and creates the required unique
indexes. `news_service.py` sends an HTTP request to NewsAPI.org using the API
key from `.env`. It checks the response, parses the JSON, extracts article
fields, and assigns each article a category using editable keywords.

`database.py` inserts the prepared article documents into the `news`
collection. MongoDB rejects URLs that already exist because `url` has a unique
index; the application counts those as skipped duplicates. The briefing
service scores the fetched stories using category, important words, and
publication recency. It selects top stories, organizes them into briefing
sections, adds learning and career suggestions, and formats the briefing.
`database.py` saves one briefing document per date, replacing that date's
briefing if the job is run again.

Separately, Flask routes in `main.py` let a browser or Postman query the
MongoDB collections. They return results as JSON. The browser dashboard calls
the same API routes to show articles, search results, category filters,
connection status, and briefings.

### 2. Why do you need a scheduler, and how exactly does it trigger your Python function?

A scheduler runs the news job without someone manually starting it every day.
It helps automate regular collection and briefing generation.

For the fixed daily schedule, `scheduler.py` creates an APScheduler
`BlockingScheduler` and registers `run_daily_job` with a cron trigger. The
trigger receives `NEWS_SCHEDULE_HOUR` and `NEWS_SCHEDULE_MINUTE` from
`config.py`, which reads them from `.env` (6:00 AM by default). While the
Python process is running, APScheduler waits for the configured local time.
When the time matches, it calls `run_daily_job()`.

The dashboard interval schedule uses an APScheduler `BackgroundScheduler`.
When a user selects an interval and clicks **Start auto refresh**, the app
starts one collection immediately and then repeats at the selected interval.
The dashboard checks scheduler status and reloads the displayed news and
briefing after a run completes. These schedules live inside the running Python
process; they are not independent Windows services.

### 3. What happens if the application or server is stopped at 6:00 AM when the schedule is for 7:00 AM?

If the application is stopped at 6:00 AM but is started again before 7:00 AM,
the process can be running when the 7:00 AM trigger arrives, so the job can run
as scheduled.

If the application is stopped at 7:00 AM, the Python scheduler cannot call the
function because the process is not running. This beginner project does not
save missed scheduler events or automatically replay them. If the app starts
after that day's 7:00 AM run time, the next cron-triggered run is normally at
7:00 AM the following day. A user can manually run `run_daily_job()` to collect
news sooner.

The dashboard interval schedule also stops when the Flask process exits. It
must be started again from the dashboard after Flask restarts. For the
dashboard schedule to update the browser automatically, both Flask and the
browser page need to remain open; collection itself runs in the Flask process.

### 4. How do you prevent duplicate news in MongoDB?

`initialize_database()` creates a unique MongoDB index on the `url` field in
the `news` collection. Before MongoDB accepts an insert, it checks that no
document already has exactly that indexed URL. If the URL already exists,
MongoDB raises a duplicate-key error instead of inserting a second document.

`save_articles()` catches that specific duplicate-key error and increments
the duplicate count. It continues processing the other articles and returns
two values: how many were newly inserted and how many were skipped as
duplicates. Other MongoDB errors are not silently treated as duplicates.

This is exact URL-based deduplication. If two sources use different URLs for
the same story, this simple project may store both; detecting that case would
require additional normalization or story-matching logic.

### 5. Explain how news travels from the external API to Python to MongoDB to the REST API and Postman.

1. **External API to Python:** `news_service.py` uses Requests to send a
   configured HTTP request to NewsAPI.org. The API key is read from the local
   environment configuration and is sent in a request header, not printed in
   the response.
2. **JSON to article dictionaries:** Python checks the HTTP result, reads the
   JSON response, validates the article list, and extracts fields such as
   title, description, source, author, date, and URL. It adds the category and
   collection time.
3. **Python to MongoDB:** `database.py` inserts each prepared article into
   `tech_news.news`. The unique URL index prevents exact duplicate URLs.
4. **MongoDB to REST API:** A request to a Flask route in `main.py` causes
   PyMongo to query the appropriate collection. For example, `/news` sorts
   articles by publication date, while `/news/search?keyword=python` searches
   title, description, and category.
5. **REST API to Postman:** Flask converts MongoDB-specific values such as
   `ObjectId` and dates into JSON-compatible strings, then sends a JSON HTTP
   response with a status code. Postman displays that response so a developer
   can inspect the result, such as the article list, count, or an error
   message.

The UI uses the same REST routes as Postman; Postman is a tool for manually
sending and inspecting requests, not a separate data store.