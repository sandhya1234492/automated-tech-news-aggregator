const articleList = document.querySelector("#article-list");
const newsMessage = document.querySelector("#news-message");
const keywordInput = document.querySelector("#keyword-input");
const categorySelect = document.querySelector("#category-select");
const healthStatus = document.querySelector("#health-status");
const healthIndicator = document.querySelector("#health-indicator");
const briefingDate = document.querySelector("#briefing-date");
const briefingMessage = document.querySelector("#briefing-message");
const briefingContent = document.querySelector("#briefing-content");
const schedulerBadge = document.querySelector("#scheduler-badge");
const schedulerMessage = document.querySelector("#scheduler-message");
const scheduleInterval = document.querySelector("#schedule-interval");
const startScheduleButton = document.querySelector("#start-schedule-button");
const stopScheduleButton = document.querySelector("#stop-schedule-button");
let lastCompletedRun = null;
let schedulerRequestInProgress = false;

function setMessage(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("is-error", isError);
}

async function requestJson(url) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}.`);
  }
  return data;
}

async function sendJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}.`);
  }
  return data;
}

function makeElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function formatDate(value) {
  if (!value) return "Publication date unavailable";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "Publication date unavailable"
    : parsed.toLocaleString();
}

function renderArticles(articles) {
  articleList.replaceChildren();

  if (articles.length === 0) {
    articleList.append(makeElement("p", "message", "No matching articles found."));
    return;
  }

  for (const article of articles) {
    const card = makeElement("article", "article-card");
    const category = makeElement(
      "span",
      "category-tag",
      article.category || "Other Technology",
    );
    const heading = makeElement("h3");
    const link = makeElement("a", "", article.title || "Untitled article");
    const summary = makeElement(
      "p",
      "article-description",
      article.description || "No description was provided by the source.",
    );
    const metadata = makeElement("div", "article-meta");
    const source = makeElement("span", "", article.source || "Unknown source");
    const published = makeElement("span", "", formatDate(article.published_at));

    try {
      const articleUrl = new URL(article.url);
      if (articleUrl.protocol === "https:" || articleUrl.protocol === "http:") {
        link.href = articleUrl.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
      } else {
        link.removeAttribute("href");
      }
    } catch {
      link.removeAttribute("href");
    }

    heading.append(link);
    metadata.append(source, published);
    card.append(category, heading, summary, metadata);
    articleList.append(card);
  }
}

async function loadNews() {
  articleList.replaceChildren();
  setMessage(newsMessage, "Loading articles…");

  const keyword = keywordInput.value.trim();
  const category = categorySelect.value;
  let endpoint = "/news?limit=50";

  if (keyword) {
    endpoint = `/news/search?${new URLSearchParams({ keyword, limit: "50" })}`;
  } else if (category) {
    endpoint = `/news/category/${encodeURIComponent(category)}?limit=50`;
  }

  try {
    const result = await requestJson(endpoint);
    renderArticles(result.items || []);
    setMessage(newsMessage, `${result.count} article(s) returned.`);
  } catch (error) {
    setMessage(newsMessage, error.message, true);
  }
}

async function checkHealth() {
  healthIndicator.className = "health-indicator";
  healthStatus.textContent = "Checking API and database…";
  try {
    const result = await requestJson("/health");
    healthIndicator.classList.add("is-online");
    healthStatus.textContent = `API online · Database ${result.database}`;
  } catch (error) {
    healthIndicator.classList.add("is-offline");
    healthStatus.textContent = error.message;
  }
}

async function loadBriefing(event) {
  if (event) {
    event.preventDefault();
  }
  briefingContent.textContent = "";
  const selectedDate = briefingDate.value;
  if (!selectedDate) {
    setMessage(briefingMessage, "Choose a briefing date.", true);
    return;
  }

  setMessage(briefingMessage, "Loading briefing…");
  try {
    const briefing = await requestJson(`/briefings/${selectedDate}`);
    briefingContent.textContent =
      briefing.text || JSON.stringify(briefing, null, 2);
    setMessage(
      briefingMessage,
      `${briefing.total_news ?? 0} article(s) in the ${briefing.briefing_date} briefing.`,
    );
  } catch (error) {
    setMessage(briefingMessage, error.message, true);
  }
}

function formatRunTime(value) {
  if (!value) return "Not run yet";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown" : parsed.toLocaleString();
}

function setSchedulerBusy(isBusy) {
  schedulerRequestInProgress = isBusy;
  startScheduleButton.disabled = isBusy;
  stopScheduleButton.disabled = isBusy || schedulerBadge.dataset.running !== "true";
  scheduleInterval.disabled = isBusy;
}

async function refreshSchedulerStatus() {
  if (schedulerRequestInProgress) return;

  try {
    const status = await requestJson("/scheduler/status");
    const isRunning = status.running === true;
    schedulerBadge.dataset.running = String(isRunning);
    schedulerBadge.textContent = isRunning
      ? `Running · ${status.interval_label || status.interval}`
      : "Stopped";
    schedulerBadge.classList.toggle("is-running", isRunning);
    stopScheduleButton.disabled = !isRunning;

    let statusText = isRunning
      ? `Next collection: ${formatRunTime(status.next_run_time)}.`
      : "Automatic collection is stopped.";
    if (status.last_started) {
      statusText += ` Last run started: ${formatRunTime(status.last_started)}.`;
    }
    if (status.last_error) {
      statusText += ` ${status.last_error}`;
    }
    setMessage(schedulerMessage, statusText, Boolean(status.last_error));

    if (status.last_completed && status.last_completed !== lastCompletedRun) {
      lastCompletedRun = status.last_completed;
      await Promise.all([loadNews(), loadBriefing()]);
      setMessage(
        schedulerMessage,
        status.last_error
          ? status.last_error
          : `Collection finished at ${formatRunTime(status.last_completed)}. News and briefing refreshed.`,
        Boolean(status.last_error),
      );
    }
  } catch (error) {
    setMessage(schedulerMessage, error.message, true);
  }
}

async function startSchedule() {
  setSchedulerBusy(true);
  setMessage(schedulerMessage, "Starting the schedule and collecting news…");
  try {
    await sendJson("/scheduler/start", { interval: scheduleInterval.value });
    await refreshSchedulerStatus();
  } catch (error) {
    setMessage(schedulerMessage, error.message, true);
  } finally {
    setSchedulerBusy(false);
    await refreshSchedulerStatus();
  }
}

async function stopSchedule() {
  setSchedulerBusy(true);
  try {
    await sendJson("/scheduler/stop");
    setMessage(schedulerMessage, "Automatic collection stopped.");
    await refreshSchedulerStatus();
  } catch (error) {
    setMessage(schedulerMessage, error.message, true);
  } finally {
    setSchedulerBusy(false);
  }
}

document.querySelector("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  loadNews();
});
document.querySelector("#latest-button").addEventListener("click", () => {
  keywordInput.value = "";
  categorySelect.value = "";
  loadNews();
});
document.querySelector("#health-button").addEventListener("click", checkHealth);
document.querySelector("#briefing-form").addEventListener("submit", loadBriefing);
startScheduleButton.addEventListener("click", startSchedule);
stopScheduleButton.addEventListener("click", stopSchedule);

briefingDate.value = new Date().toISOString().slice(0, 10);
checkHealth();
loadNews();
loadBriefing(new Event("submit", { cancelable: true }));
refreshSchedulerStatus();
window.setInterval(refreshSchedulerStatus, 5000);
