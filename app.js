const state = {
  catalog: [],
  meta: null,
  typeFilter: "all",
};

const TYPE_GROUPS = {
  all: new Set(),
  movie: new Set(["movie"]),
  tv: new Set(["tvSeries", "tvMiniSeries", "tvMovie", "tvEpisode", "tvShort", "tvSpecial"]),
  short: new Set(["short", "tvShort"]),
};

const GENRE_LEXICON = {
  Action: ["action", "fight", "combat", "explosive", "chase", "adrenaline", "battle"],
  Adventure: ["adventure", "journey", "quest", "exploration", "fun", "adventurous"],
  Animation: ["animated", "animation", "anime", "cartoon"],
  Biography: ["biography", "biopic", "true story", "real person", "life story"],
  Comedy: ["funny", "comedy", "comedic", "laugh", "hilarious", "joyful", "joyous", "cheerful", "silly", "smart comedy"],
  Crime: ["crime", "criminal", "detective", "police", "murder", "heist", "mafia"],
  Documentary: ["documentary", "true story", "nonfiction", "real life", "educational"],
  Drama: ["drama", "emotional", "human", "serious", "character"],
  Family: ["family", "kids", "children", "wholesome", "safe", "easy to watch"],
  Fantasy: ["fantasy", "magic", "magical", "mythical", "kingdom"],
  Horror: ["horror", "scary", "creepy", "terrifying", "haunted", "zombie", "monster"],
  Music: ["music", "musician", "band", "concert", "singer"],
  Musical: ["musical", "singing", "song and dance"],
  Mystery: ["mystery", "twist", "twists", "clever", "puzzle", "investigation", "mind bending"],
  Romance: ["romance", "romantic", "love", "relationship", "date night"],
  "Sci-Fi": ["sci fi", "sci-fi", "scifi", "science fiction", "future", "futuristic", "space", "alien", "robot"],
  Sport: ["sport", "sports", "athlete", "competition", "football", "basketball"],
  Thriller: ["thriller", "tense", "intense", "suspense", "dangerous", "edge of my seat"],
  War: ["war", "battlefield", "soldier", "military"],
  Western: ["western", "cowboy", "frontier", "outlaw"],
};

const MOOD_LEXICON = {
  comforting: ["comforting", "cozy", "warm", "gentle", "easy", "safe", "wholesome", "calm"],
  joyful: ["joyful", "joyous", "cheerful", "happy", "bright", "good mood"],
  funny: ["funny", "comedy", "comedic", "laugh", "hilarious", "silly"],
  hopeful: ["hopeful", "uplifting", "inspiring", "optimistic", "positive"],
  romantic: ["romantic", "romance", "love", "relationship"],
  tense: ["tense", "intense", "suspense", "thriller", "anxious"],
  dark: ["dark", "disturbing", "grim", "bleak", "violent"],
  sad: ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief"],
  adventurous: ["adventurous", "adventure", "quest", "journey", "exciting"],
  mind_bending: ["mind bending", "twisty", "surreal", "psychological"],
};

const AVOID_MAP = {
  dark: ["dark", "disturbing", "grim", "bleak", "violent", "unsettling"],
  sad: ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief"],
  scary: ["scary", "horror", "creepy", "terrifying", "haunted", "monster", "zombie"],
  violent: ["violent", "violence", "intense", "tense", "war", "battle", "murder"],
};

const TYPO_ALIASES = {
  commedy: "comedy",
  comdy: "comedy",
  joyus: "joyous",
  joyfull: "joyful",
  hartbroken: "heartbroken",
  "heart broken": "heartbroken",
  scarry: "scary",
  thriler: "thriller",
  futurstic: "futuristic",
  wholsome: "wholesome",
  dont: "do not",
  wanna: "want to",
};

const $ = (selector) => document.querySelector(selector);

function normalize(text) {
  let value = String(text || "").toLowerCase().replace(/[’]/g, "'");
  Object.entries(TYPO_ALIASES).forEach(([bad, good]) => {
    value = value.replace(new RegExp(`\\b${escapeRegExp(bad)}\\b`, "g"), good);
  });
  return value.replace(/[^a-z0-9#+\-' ]+/g, " ").replace(/\s+/g, " ").trim();
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function includesPhrase(text, phrase) {
  return new RegExp(`(^|\\s)${escapeRegExp(phrase)}($|\\s)`).test(text);
}

function phraseNegated(text, phrase) {
  const index = text.indexOf(phrase);
  if (index < 0) return false;
  const before = text.slice(0, index).split(/\bbut\b|\bhowever\b|\bthough\b|\bsomething\b|\bmore\b|\bjust\b/).pop();
  const window = before.trim().split(/\s+/).slice(-5).join(" ");
  return /\b(no|not|never|without|avoid|exclude|nothing|do not|dont)\b/.test(window);
}

function detectTypeFromPrompt(prompt) {
  const text = normalize(prompt);
  if (/\b(movie|movies|film|films)\b/.test(text) && !/\b(show|shows|series|tv|television)\b/.test(text)) return "movie";
  if (/\b(show|shows|series|tv series|television)\b/.test(text) && !/\b(movie|movies|film|films)\b/.test(text)) return "tv";
  if (/\b(short|shorts)\b/.test(text)) return "short";
  return null;
}

function parseIntent(prompt) {
  const text = normalize(prompt);
  const desiredMarker = /(i want|want|need|looking for|give me|recommend|show me|in the mood for)/.exec(text);
  const stateOnly = /\b(i feel|i am feeling|feeling|i am|im|i'm)\b/.test(text) && /\b(sad|heartbroken|down|anxious|stressed|angry|tired)\b/.test(text);
  let desiredText = desiredMarker ? text.slice(desiredMarker.index) : text;
  const inferredGenres = inferWeightedSignals(text, GENRE_LEXICON);
  const inferredMoods = inferWeightedSignals(desiredText, MOOD_LEXICON);
  const avoidSignals = inferAvoidSignals(text);
  const typeFromPrompt = detectTypeFromPrompt(text);

  if (stateOnly && Object.keys(inferredGenres).length === 0) {
    inferredGenres.Comedy = Math.max(inferredGenres.Comedy || 0, 0.85);
    inferredGenres.Family = Math.max(inferredGenres.Family || 0, 0.55);
    inferredMoods.comforting = Math.max(inferredMoods.comforting || 0, 1);
    inferredMoods.joyful = Math.max(inferredMoods.joyful || 0, 0.75);
    avoidSignals.sad = 1;
    avoidSignals.dark = 1;
  }

  return { text, desiredText, inferredGenres, inferredMoods, avoidSignals, typeFromPrompt };
}

function inferWeightedSignals(text, lexicon) {
  const result = {};
  Object.entries(lexicon).forEach(([label, phrases]) => {
    let hits = 0;
    phrases.forEach((phrase) => {
      if (includesPhrase(text, phrase) && !phraseNegated(text, phrase)) hits += 1;
    });
    if (hits) result[label] = Math.min(1, 0.55 + hits * 0.18);
  });
  return result;
}

function inferAvoidSignals(text) {
  const result = {};
  Object.entries(AVOID_MAP).forEach(([label, phrases]) => {
    if (phrases.some((phrase) => phraseNegated(text, phrase))) result[label] = 1;
  });
  if (/do not destroy me|dont destroy me|not destroy me|not wreck me/.test(text)) {
    result.sad = 1;
    result.dark = 1;
  }
  return result;
}

function typeMatches(item, typeFilter) {
  if (typeFilter === "all") return true;
  return TYPE_GROUPS[typeFilter]?.has(item.type) ?? true;
}

function facetScore(item, category, wanted) {
  if (!wanted || !item.facets?.[category]) return 0;
  return item.facets[category].reduce((sum, facet) => {
    return sum + (wanted[facet.label] ? wanted[facet.label] * Math.max(facet.score, 0.08) : 0);
  }, 0);
}

function textScore(item, intent) {
  const tokens = intent.desiredText.split(/\s+/).filter((token) => token.length > 3);
  if (!tokens.length) return 0;
  const hits = tokens.filter((token) => item.searchText.includes(token)).length;
  return Math.min(1, hits / Math.min(tokens.length, 12));
}

function genreScore(item, inferredGenres, selectedGenre) {
  const genres = new Set(item.genres);
  let score = 0;
  const entries = Object.entries(inferredGenres);
  if (entries.length) {
    const total = entries.reduce((sum, [, weight]) => sum + weight, 0);
    score += entries.reduce((sum, [genre, weight]) => sum + (genres.has(genre) ? weight : 0), 0) / Math.max(total, 0.01);
  }
  if (selectedGenre !== "all") score += genres.has(selectedGenre) ? 0.8 : -0.45;
  return score;
}

function avoidPenalty(item, avoidSignals, extraAvoid) {
  const allAvoids = { ...avoidSignals };
  if (extraAvoid !== "none") allAvoids[extraAvoid] = 1;
  let penalty = 0;
  const text = item.searchText;
  Object.entries(allAvoids).forEach(([avoid, weight]) => {
    const phrases = AVOID_MAP[avoid] || [];
    if (phrases.some((phrase) => text.includes(phrase))) penalty += 0.18 * weight;
    Object.values(item.facets || {}).flat().forEach((facet) => {
      if (phrases.includes(facet.label)) penalty += Math.max(facet.score, 0.05) * 0.32 * weight;
    });
    if (avoid === "scary" && item.genres.includes("Horror")) penalty += 0.45;
    if (avoid === "violent" && (item.genres.includes("War") || item.genres.includes("Action"))) penalty += 0.18;
  });
  return Math.min(0.75, penalty);
}

function scoreItem(item, intent, controls) {
  const genre = genreScore(item, intent.inferredGenres, controls.genre);
  const mood = facetScore(item, "mood", intent.inferredMoods) + facetScore(item, "arc", intent.inferredMoods);
  const text = textScore(item, intent);
  const quality = Math.min(1, (item.weightedRating || item.rating || 0) / 9.2);
  const popularity = Math.min(1, Math.log10((item.votes || 0) + 1) / 6.5);
  const topic = item.lowConfidence ? 0.82 : 1;
  const penalty = avoidPenalty(item, intent.avoidSignals, controls.avoid);
  const score = ((text * 0.34) + (genre * 0.28) + (mood * 0.22) + (quality * 0.11) + (popularity * 0.05) - penalty) * topic;
  return Math.max(0, Math.min(1, score));
}

function getControls() {
  return {
    prompt: $("#promptInput").value,
    genre: $("#genreSelect").value,
    mood: $("#moodSelect").value,
    avoid: $("#avoidSelect").value,
    rating: Number($("#ratingRange").value),
    votes: Number($("#votesRange").value),
    yearFrom: Number($("#yearFrom").value),
    yearTo: Number($("#yearTo").value),
    limit: Number($("#limitSelect").value),
    sort: $("#sortSelect").value,
  };
}

function runRecommendation() {
  const controls = getControls();
  const intent = parseIntent(controls.prompt);
  const effectiveType = intent.typeFromPrompt || state.typeFilter;
  const moods = controls.mood === "all" ? intent.inferredMoods : { ...intent.inferredMoods, [controls.mood]: 1 };
  const mergedIntent = { ...intent, inferredMoods: moods };

  const scored = state.catalog
    .filter((item) => typeMatches(item, effectiveType))
    .filter((item) => (item.rating || 0) >= controls.rating)
    .filter((item) => (item.votes || 0) >= controls.votes)
    .filter((item) => item.year >= controls.yearFrom && item.year <= controls.yearTo)
    .map((item) => ({ item, score: scoreItem(item, mergedIntent, controls) }))
    .filter(({ score }) => score > 0.05);

  scored.sort((a, b) => {
    if (controls.sort === "rating") return (b.item.weightedRating || 0) - (a.item.weightedRating || 0);
    if (controls.sort === "popular") return (b.item.votes || 0) - (a.item.votes || 0);
    if (controls.sort === "recent") return (b.item.year || 0) - (a.item.year || 0);
    return b.score - a.score;
  });

  const results = scored.slice(0, controls.limit);
  renderStatus(intent, effectiveType, results.length, controls);
  renderResults(results, mergedIntent, controls);
}

function renderStatus(intent, effectiveType, count, controls) {
  $("#resultCount").textContent = count.toLocaleString();
  const typeNote = intent.typeFromPrompt ? `Prompt locked format to ${labelType(effectiveType)}.` : `Showing ${labelType(effectiveType)}.`;
  $("#detectedIntent").textContent = typeNote;

  const genres = Object.keys(intent.inferredGenres);
  const avoids = [controls.avoid !== "none" ? controls.avoid : null, ...Object.keys(intent.avoidSignals)].filter(Boolean);
  $("#intentSummary").textContent = [
    genres.length ? `Inferred ${genres.join(", ")}.` : "No specific genre forced.",
    avoids.length ? `Avoiding ${[...new Set(avoids)].join(", ")}.` : "No extra avoid rule.",
  ].join(" ");
}

function labelType(type) {
  return ({ all: "all formats", movie: "movies", tv: "TV", short: "shorts" }[type] || type);
}

function renderResults(results, intent, controls) {
  const root = $("#results");
  root.innerHTML = "";
  if (!results.length) {
    root.innerHTML = '<div class="empty">No matches passed the filters. Try lowering the vote/rating threshold or widening the format selector.</div>';
    return;
  }

  const template = $("#cardTemplate");
  results.forEach(({ item, score }) => {
    const node = template.content.cloneNode(true);
    const poster = node.querySelector(".poster");
    const fallback = node.querySelector(".poster-fallback");

    fallback.textContent = item.title;
    poster.alt = `${item.title} poster`;
    setPoster(poster, item.posterUrl);
    node.querySelector(".format").textContent = `${labelContentType(item.type)}${item.year ? ` • ${item.year}` : ""}`;
    node.querySelector(".match-badge").textContent = `${Math.round(score * 100)}% match`;
    node.querySelector("h3").textContent = item.title;
    node.querySelector(".meta").textContent = `${item.genres.join(", ")} • ${item.rating?.toFixed(1) || "N/A"} rating • ${formatVotes(item.votes)} votes`;
    node.querySelector(".description").textContent = item.description;

    const tags = node.querySelector(".tags");
    [...item.genres.slice(0, 3), item.facets?.mood?.[0]?.label, item.facets?.tone?.[0]?.label].filter(Boolean).forEach((tag) => {
      const span = document.createElement("span");
      span.textContent = tag;
      tags.appendChild(span);
    });
    node.querySelector(".why").textContent = buildWhy(item, intent, controls, score);
    root.appendChild(node);
  });
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

function formatVotes(value) {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${Math.round(value / 1000)}K`;
  return value.toLocaleString();
}

function buildWhy(item, intent, controls, score) {
  const topMood = item.facets?.mood?.slice(0, 2).map((f) => f.label).join(", ");
  const topArc = item.facets?.arc?.slice(0, 2).map((f) => f.label).join(", ");
  const genreMatch = Object.keys(intent.inferredGenres).filter((genre) => item.genres.includes(genre));
  return [
    `Match score: ${Math.round(score * 100)}%.`,
    genreMatch.length ? `Genre intent matched: ${genreMatch.join(", ")}.` : "Matched through prompt language, NLP topic, and facets.",
    topMood ? `Mood signals: ${topMood}.` : "",
    topArc ? `Emotional arc: ${topArc}.` : "",
    item.topic ? `Topic: ${item.topic}.` : "",
  ].filter(Boolean).join(" ");
}

function populateFilters() {
  state.meta.genres.forEach((genre) => {
    const option = document.createElement("option");
    option.value = genre;
    option.textContent = genre;
    $("#genreSelect").appendChild(option);
  });
  Object.keys(MOOD_LEXICON).forEach((mood) => {
    const option = document.createElement("option");
    option.value = mood;
    option.textContent = mood.replace(/_/g, " ");
    $("#moodSelect").appendChild(option);
  });
  $("#yearFrom").value = state.meta.yearMin;
  $("#yearTo").value = state.meta.yearMax;
  $("#catalogStatus").textContent = `Connected to ${state.meta.count.toLocaleString()} catalog titles`;
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
      runRecommendation();
    });
  });
  document.querySelectorAll("#typeSegments button").forEach((button) => {
    button.addEventListener("click", () => {
      state.typeFilter = button.dataset.type;
      document.querySelectorAll("#typeSegments button").forEach((item) => item.classList.toggle("active", item === button));
      runRecommendation();
    });
  });
  ["genreSelect", "moodSelect", "avoidSelect", "ratingRange", "votesRange", "yearFrom", "yearTo", "limitSelect", "sortSelect"].forEach((id) => {
    $(`#${id}`).addEventListener("input", () => {
      updateRanges();
      runRecommendation();
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
  const response = await fetch("assets/data/catalog.json");
  const data = await response.json();
  state.catalog = data.items;
  state.meta = data.meta;
  populateFilters();
  bindEvents();
  updateRanges();
  runRecommendation();
}

init().catch((error) => {
  console.error(error);
  $("#catalogStatus").textContent = "Catalog failed to load";
  $("#results").innerHTML = '<div class="empty">The catalog could not be loaded. Please run this through a local server or Netlify.</div>';
});
