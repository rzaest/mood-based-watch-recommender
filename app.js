const state = {
  typeFilter: "all",
  summary: null,
  requestId: 0,
  activeController: null,
  debounceTimer: null,
};

const API_BASE_URL = (window.MBWR_API_BASE_URL || getDefaultApiBase()).replace(/\/$/, "");

const $ = (selector) => document.querySelector(selector);

function getDefaultApiBase() {
  const localHost = ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
  if (localHost && window.location.port && window.location.port !== "8000") {
    return "http://localhost:8000";
  }
  return "";
}

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === "object" ? data.detail || data.message : data;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function getControls() {
  const yearMin = Number(state.summary?.year_min || 1990);
  const yearMax = Number(state.summary?.year_max || 2023);
  const yearFrom = Number($("#yearFrom").value);
  const yearTo = Number($("#yearTo").value);
  return {
    prompt: $("#promptInput").value,
    type: state.typeFilter,
    genre: $("#genreSelect").value,
    mood: $("#moodSelect").value,
    avoid: $("#avoidSelect").value,
    min_rating: Number($("#ratingRange").value),
    min_votes: Number($("#votesRange").value),
    year_from: Number.isFinite(yearFrom) && yearFrom >= 1800 ? yearFrom : yearMin,
    year_to: Number.isFinite(yearTo) && yearTo >= 1800 ? yearTo : yearMax,
    limit: Number($("#limitSelect").value),
    sort: $("#sortSelect").value,
  };
}

async function runRecommendation() {
  const controls = getControls();
  if (controls.year_from > controls.year_to) {
    renderError("Year from must be less than or equal to year to.");
    return;
  }
  const requestId = ++state.requestId;
  if (state.activeController) state.activeController.abort();
  state.activeController = new AbortController();
  setLoading(true);
  try {
    const data = await apiFetch("/recommend", {
      method: "POST",
      body: JSON.stringify(controls),
      signal: state.activeController.signal,
    });
    if (requestId !== state.requestId) return;
    renderStatus(data, controls);
    renderResults(data.results || [], data.message);
  } catch (error) {
    if (error.name === "AbortError" || requestId !== state.requestId) return;
    renderError(error.message || "The recommendation service could not be reached.");
  } finally {
    if (requestId === state.requestId) setLoading(false);
  }
}

function scheduleRecommendation() {
  clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(runRecommendation, 180);
}

function setLoading(isLoading) {
  $("#recommendButton").disabled = isLoading;
  $("#recommendButton").textContent = isLoading ? "Finding..." : "Recommend";
}

function renderStatus(data, controls) {
  $("#resultCount").textContent = Number(data.count || 0).toLocaleString();
  const typeNote = data.effective_type !== controls.type
    ? `Prompt locked format to ${labelType(data.effective_type)}.`
    : `Showing ${labelType(data.effective_type)}.`;
  $("#detectedIntent").textContent = typeNote;

  const genres = data.inferred_genres || [];
  const avoids = data.avoided_signals || [];
  $("#intentSummary").textContent = [
    data.seed_title ? `Using seed title: ${data.seed_title}.` : null,
    genres.length ? `Inferred ${genres.join(", ")}.` : "No specific genre forced.",
    avoids.length ? `Avoiding ${avoids.join(", ")}.` : "No extra avoid rule.",
  ].filter(Boolean).join(" ");
}

function labelType(type) {
  return ({ all: "all formats", movie: "movies", tv: "TV", short: "shorts" }[type] || type);
}

function renderResults(results, message) {
  const root = $("#results");
  root.innerHTML = "";
  if (!results.length) {
    root.innerHTML = `<div class="empty">${escapeHtml(message || "No matches passed the filters. Try lowering the vote/rating threshold or widening the format selector.")}</div>`;
    return;
  }

  const template = $("#cardTemplate");
  results.forEach((item) => {
    const node = template.content.cloneNode(true);
    const poster = node.querySelector(".poster");
    const fallback = node.querySelector(".poster-fallback");

    fallback.textContent = item.title;
    poster.alt = `${item.title} poster`;
    setPoster(poster, item.poster_url);
    node.querySelector(".format").textContent = `${item.type_label || labelContentType(item.type)}${item.year ? ` • ${item.year}` : ""}`;
    node.querySelector(".match-badge").textContent = `${Math.round((item.match_score || 0) * 100)}% match`;
    node.querySelector("h3").textContent = item.title;
    node.querySelector(".meta").textContent = `${(item.genres || []).join(", ")} • ${formatRating(item.rating)} rating • ${formatVotes(item.votes || 0)} votes`;
    node.querySelector(".description").textContent = item.description || "";

    const tags = node.querySelector(".tags");
    [...(item.genres || []).slice(0, 3), ...(item.moods || []).slice(0, 2)].filter(Boolean).forEach((tag) => {
      const span = document.createElement("span");
      span.textContent = tag;
      tags.appendChild(span);
    });
    node.querySelector(".why").textContent = item.why || "";
    root.appendChild(node);
  });
}

function renderError(message) {
  $("#resultCount").textContent = "0";
  $("#detectedIntent").textContent = "Backend request failed.";
  $("#intentSummary").textContent = "Check that the FastAPI backend is running and reachable.";
  $("#results").innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
}

function setPoster(image, url) {
  image.classList.remove("loaded");
  image.removeAttribute("src");
  if (!url) return;
  image.onload = () => image.classList.add("loaded");
  image.onerror = () => image.classList.remove("loaded");
  image.src = url;
}

function labelContentType(type) {
  return ({
    movie: "Movie",
    tvSeries: "TV series",
    tvMiniSeries: "TV miniseries",
    tvMovie: "TV movie",
    tvEpisode: "TV episode",
    short: "Short",
    tvShort: "TV short",
    tvSpecial: "TV special",
    video: "Video",
    videoGame: "Video game",
  }[type] || type);
}

function formatRating(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(1) : "N/A";
}

function formatVotes(value) {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${Math.round(value / 1000)}K`;
  return Number(value || 0).toLocaleString();
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function populateFilters(summary) {
  state.summary = summary;
  $("#genreSelect").innerHTML = '<option value="all">Any genre</option>';
  $("#moodSelect").innerHTML = '<option value="all">Any mood</option>';

  (summary.genres || []).forEach((genre) => {
    const option = document.createElement("option");
    option.value = genre;
    option.textContent = genre;
    $("#genreSelect").appendChild(option);
  });
  (summary.moods || []).forEach((mood) => {
    const option = document.createElement("option");
    option.value = mood;
    option.textContent = mood.replace(/_/g, " ");
    $("#moodSelect").appendChild(option);
  });
  $("#yearFrom").value = summary.year_min || 1990;
  $("#yearTo").value = summary.year_max || 2023;
  $("#catalogStatus").textContent = `Backend connected to ${Number(summary.total_titles || 0).toLocaleString()} catalog titles`;
}

function bindEvents() {
  $("#recommendButton").addEventListener("click", runRecommendation);
  $("#resetButton").addEventListener("click", () => {
    $("#promptInput").value = "I feel sad and heartbroken and I want to watch something joyous and comedic";
    $("#genreSelect").value = "all";
    $("#moodSelect").value = "all";
    $("#avoidSelect").value = "none";
    $("#ratingRange").value = "6.5";
    $("#votesRange").value = "30000";
    $("#sortSelect").value = "match";
    state.typeFilter = "all";
    document.querySelectorAll("#typeSegments button").forEach((button) => button.classList.toggle("active", button.dataset.type === "all"));
    updateRanges();
    runRecommendation();
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      $("#promptInput").value = button.dataset.prompt;
      scheduleRecommendation();
    });
  });
  document.querySelectorAll("#typeSegments button").forEach((button) => {
    button.addEventListener("click", () => {
      state.typeFilter = button.dataset.type;
      document.querySelectorAll("#typeSegments button").forEach((item) => item.classList.toggle("active", item === button));
      scheduleRecommendation();
    });
  });
  ["genreSelect", "moodSelect", "avoidSelect", "ratingRange", "votesRange", "yearFrom", "yearTo", "limitSelect", "sortSelect"].forEach((id) => {
    $(`#${id}`).addEventListener("input", () => {
      updateRanges();
      scheduleRecommendation();
    });
  });
  $("#promptInput").addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") runRecommendation();
  });
}

function updateRanges() {
  $("#ratingValue").textContent = `${Number($("#ratingRange").value).toFixed(1)}+`;
  $("#votesValue").textContent = `${Number($("#votesRange").value).toLocaleString()}+`;
}

async function init() {
  bindEvents();
  updateRanges();
  try {
    const summary = await apiFetch("/catalog/summary");
    populateFilters(summary);
    await runRecommendation();
  } catch (error) {
    $("#catalogStatus").textContent = "Backend not connected";
    renderError(error.message || "Could not connect to the recommendation backend.");
  }
}

init();
