import math
import re
from dataclasses import dataclass
from typing import Any

from .schemas import CatalogItem, CatalogSummary, RecommendRequest, RecommendResponse, RecommendationResult


TYPE_GROUPS = {
    "all": set(),
    "movie": {"movie"},
    "tv": {"tvSeries", "tvMiniSeries", "tvMovie", "tvEpisode", "tvShort", "tvSpecial"},
    "short": {"short", "tvShort"},
}

GENRE_LEXICON = {
    "Action": ["action", "fight", "combat", "explosive", "chase", "adrenaline", "battle"],
    "Adventure": ["adventure", "journey", "quest", "exploration", "fun", "adventurous"],
    "Animation": ["animated", "animation", "anime", "cartoon"],
    "Biography": ["biography", "biopic", "true story", "real person", "life story"],
    "Comedy": ["funny", "comedy", "comedic", "laugh", "hilarious", "joyful", "joyous", "cheerful", "silly", "smart comedy"],
    "Crime": ["crime", "criminal", "detective", "police", "murder", "heist", "mafia"],
    "Documentary": ["documentary", "true story", "nonfiction", "real life", "educational"],
    "Drama": ["drama", "emotional", "human", "serious", "character"],
    "Family": ["family", "kids", "children", "wholesome", "safe", "easy to watch"],
    "Fantasy": ["fantasy", "magic", "magical", "mythical", "kingdom"],
    "Horror": ["horror", "scary", "creepy", "terrifying", "haunted", "zombie", "monster"],
    "Music": ["music", "musician", "band", "concert", "singer"],
    "Musical": ["musical", "singing", "song and dance"],
    "Mystery": ["mystery", "twist", "twists", "clever", "puzzle", "investigation", "mind bending"],
    "Romance": ["romance", "romantic", "love", "relationship", "date night"],
    "Sci-Fi": ["sci fi", "sci-fi", "scifi", "science fiction", "future", "futuristic", "space", "alien", "robot"],
    "Sport": ["sport", "sports", "athlete", "competition", "football", "basketball"],
    "Thriller": ["thriller", "tense", "intense", "suspense", "dangerous", "edge of my seat"],
    "War": ["war", "battlefield", "soldier", "military"],
    "Western": ["western", "cowboy", "frontier", "outlaw"],
}

MOOD_LEXICON = {
    "comforting": ["comforting", "cozy", "warm", "gentle", "easy", "safe", "wholesome", "calm"],
    "joyful": ["joyful", "joyous", "cheerful", "happy", "bright", "good mood"],
    "funny": ["funny", "comedy", "comedic", "laugh", "hilarious", "silly"],
    "hopeful": ["hopeful", "uplifting", "inspiring", "optimistic", "positive"],
    "romantic": ["romantic", "romance", "love", "relationship"],
    "tense": ["tense", "intense", "suspense", "thriller", "anxious"],
    "dark": ["dark", "disturbing", "grim", "bleak", "violent"],
    "sad": ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief"],
    "adventurous": ["adventurous", "adventure", "quest", "journey", "exciting"],
    "mind_bending": ["mind bending", "twisty", "surreal", "psychological"],
}

AVOID_MAP = {
    "dark": ["dark", "disturbing", "grim", "bleak", "violent", "unsettling"],
    "sad": ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief"],
    "scary": ["scary", "horror", "creepy", "terrifying", "haunted", "monster", "zombie"],
    "violent": ["violent", "violence", "intense", "tense", "war", "battle", "murder"],
}

TYPO_ALIASES = {
    "commedy": "comedy",
    "comdy": "comedy",
    "joyus": "joyous",
    "joyfull": "joyful",
    "hartbroken": "heartbroken",
    "heart broken": "heartbroken",
    "scarry": "scary",
    "thriler": "thriller",
    "futurstic": "futuristic",
    "wholsome": "wholesome",
    "dont": "do not",
    "wanna": "want to",
}


@dataclass
class Intent:
    text: str
    desired_text: str
    inferred_genres: dict[str, float]
    inferred_moods: dict[str, float]
    avoid_signals: dict[str, float]
    type_from_prompt: str | None


def normalize(text: str | None) -> str:
    value = str(text or "").lower().replace("’", "'")
    for bad, good in TYPO_ALIASES.items():
        value = re.sub(rf"\b{re.escape(bad)}\b", good, value)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9#+\-' ]+", " ", value)).strip()


def includes_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(^|\s){re.escape(phrase)}($|\s)", text) is not None


def phrase_negated(text: str, phrase: str) -> bool:
    index = text.find(phrase)
    if index < 0:
        return False
    before = re.split(r"\bbut\b|\bhowever\b|\bthough\b|\bsomething\b|\bmore\b|\bjust\b", text[:index])[-1]
    window = " ".join(before.strip().split()[-5:])
    return re.search(r"\b(no|not|never|without|avoid|exclude|nothing|do not|dont)\b", window) is not None


def detect_type_from_prompt(prompt: str) -> str | None:
    text = normalize(prompt)
    asks_movie = re.search(r"\b(movie|movies|film|films)\b", text)
    asks_tv = re.search(r"\b(show|shows|series|tv series|television)\b", text)
    if asks_movie and not asks_tv:
        return "movie"
    if asks_tv and not asks_movie:
        return "tv"
    if re.search(r"\b(short|shorts)\b", text):
        return "short"
    return None


def infer_weighted_signals(text: str, lexicon: dict[str, list[str]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for label, phrases in lexicon.items():
        hits = sum(1 for phrase in phrases if includes_phrase(text, phrase) and not phrase_negated(text, phrase))
        if hits:
            result[label] = min(1.0, 0.55 + hits * 0.18)
    return result


def infer_avoid_signals(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for label, phrases in AVOID_MAP.items():
        if any(phrase_negated(text, phrase) for phrase in phrases):
            result[label] = 1
    if re.search(r"do not destroy me|dont destroy me|not destroy me|not wreck me", text):
        result["sad"] = 1
        result["dark"] = 1
    return result


def parse_intent(prompt: str) -> Intent:
    text = normalize(prompt)
    marker = re.search(r"(i want|want|need|looking for|give me|recommend|show me|in the mood for)", text)
    negative_state = re.search(r"\b(i feel|i am feeling|feeling|i am|im|i'm)\b", text) and re.search(
        r"\b(sad|heartbroken|down|anxious|stressed|angry|tired)\b", text
    )
    desired_text = text[marker.start() :] if marker else text
    inferred_genres = infer_weighted_signals(text, GENRE_LEXICON)
    inferred_moods = infer_weighted_signals(desired_text, MOOD_LEXICON)
    avoid_signals = infer_avoid_signals(text)

    positive_desire = any(mood in inferred_moods for mood in ["comforting", "joyful", "funny", "hopeful"]) or "Comedy" in inferred_genres
    if negative_state and positive_desire:
        avoid_signals["sad"] = 1
        avoid_signals["dark"] = 1

    if negative_state and not inferred_genres:
        inferred_genres["Comedy"] = max(inferred_genres.get("Comedy", 0), 0.85)
        inferred_genres["Family"] = max(inferred_genres.get("Family", 0), 0.55)
        inferred_moods["comforting"] = max(inferred_moods.get("comforting", 0), 1)
        inferred_moods["joyful"] = max(inferred_moods.get("joyful", 0), 0.75)
        avoid_signals["sad"] = 1
        avoid_signals["dark"] = 1

    return Intent(text, desired_text, inferred_genres, inferred_moods, avoid_signals, detect_type_from_prompt(text))


class MoodRecommender:
    def __init__(self, catalog: dict[str, Any]):
        self.meta = catalog["meta"]
        self.items: list[CatalogItem] = catalog["items"]

    def summary(self) -> CatalogSummary:
        return CatalogSummary(
            total_titles=len(self.items),
            year_min=self.meta.get("yearMin"),
            year_max=self.meta.get("yearMax"),
            genres=self.meta.get("genres", []),
            types=self.meta.get("types", []),
            moods=sorted(MOOD_LEXICON),
            poster_count=sum(1 for item in self.items if item.get("posterUrl")),
            source=self.meta.get("generatedFrom"),
        )

    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        if request.year_from > request.year_to:
            raise ValueError("year_from must be less than or equal to year_to.")
        if request.genre != "all" and request.genre not in self.meta.get("genres", []):
            raise ValueError(f"Unknown genre: {request.genre}")
        if request.mood != "all" and request.mood not in MOOD_LEXICON:
            raise ValueError(f"Unknown mood: {request.mood}")

        intent = parse_intent(request.prompt)
        effective_type = intent.type_from_prompt or request.type
        merged_moods = dict(intent.inferred_moods)
        if request.mood != "all":
            merged_moods[request.mood] = 1
        intent = Intent(intent.text, intent.desired_text, intent.inferred_genres, merged_moods, intent.avoid_signals, intent.type_from_prompt)

        scored: list[tuple[CatalogItem, float]] = []
        for item in self.items:
            if not self._type_matches(item, effective_type):
                continue
            if (item.get("rating") or 0) < request.min_rating:
                continue
            if (item.get("votes") or 0) < request.min_votes:
                continue
            year = item.get("year") or 0
            if year < request.year_from or year > request.year_to:
                continue
            score = self._score_item(item, intent, request)
            if score > 0.05:
                scored.append((item, score))

        scored.sort(key=lambda row: self._sort_key(row[0], row[1], request.sort), reverse=True)
        results = [self._format_result(item, score, intent, request) for item, score in scored[: request.limit]]
        avoids = sorted(set(([request.avoid] if request.avoid != "none" else []) + list(intent.avoid_signals)))

        return RecommendResponse(
            interpreted_request=intent.desired_text or "No prompt text",
            effective_type=effective_type,
            inferred_genres=list(intent.inferred_genres),
            inferred_moods=list(intent.inferred_moods),
            avoided_signals=avoids,
            count=len(results),
            message=None if results else "No matches passed the filters. Try lowering the vote/rating threshold or widening the format selector.",
            results=results,
        )

    def _type_matches(self, item: CatalogItem, type_filter: str) -> bool:
        if type_filter == "all":
            return True
        return item.get("type") in TYPE_GROUPS.get(type_filter, set())

    def _facet_score(self, item: CatalogItem, category: str, wanted: dict[str, float]) -> float:
        facets = item.get("facets", {}).get(category, [])
        return sum(wanted.get(facet.get("label"), 0) * max(float(facet.get("score") or 0), 0.08) for facet in facets)

    def _text_score(self, item: CatalogItem, intent: Intent) -> float:
        tokens = [token for token in intent.desired_text.split() if len(token) > 3]
        if not tokens:
            return 0
        search_text = item.get("searchText", "")
        hits = sum(1 for token in tokens if token in search_text)
        return min(1, hits / min(len(tokens), 12))

    def _genre_score(self, item: CatalogItem, inferred_genres: dict[str, float], selected_genre: str) -> float:
        genres = set(item.get("genres", []))
        score = 0.0
        if inferred_genres:
            total = sum(inferred_genres.values())
            score += sum(weight for genre, weight in inferred_genres.items() if genre in genres) / max(total, 0.01)
        if selected_genre != "all":
            score += 0.8 if selected_genre in genres else -0.45
        return score

    def _avoid_penalty(self, item: CatalogItem, avoid_signals: dict[str, float], extra_avoid: str) -> float:
        all_avoids = dict(avoid_signals)
        if extra_avoid != "none":
            all_avoids[extra_avoid] = 1
        penalty = 0.0
        text = item.get("searchText", "")
        facets = [facet for group in item.get("facets", {}).values() for facet in group]
        for avoid, weight in all_avoids.items():
            phrases = AVOID_MAP.get(avoid, [])
            if any(phrase in text for phrase in phrases):
                penalty += 0.18 * weight
            for facet in facets:
                if facet.get("label") in phrases:
                    penalty += max(float(facet.get("score") or 0), 0.05) * 0.32 * weight
            genres = item.get("genres", [])
            if avoid == "scary" and "Horror" in genres:
                penalty += 0.45
            if avoid == "violent" and ("War" in genres or "Action" in genres):
                penalty += 0.18
        return min(0.75, penalty)

    def _score_item(self, item: CatalogItem, intent: Intent, request: RecommendRequest) -> float:
        genre = self._genre_score(item, intent.inferred_genres, request.genre)
        mood = self._facet_score(item, "mood", intent.inferred_moods) + self._facet_score(item, "arc", intent.inferred_moods)
        text = self._text_score(item, intent)
        quality = min(1, (item.get("weightedRating") or item.get("rating") or 0) / 9.2)
        popularity = min(1, math.log10((item.get("votes") or 0) + 1) / 6.5)
        topic = 0.82 if item.get("lowConfidence") else 1
        penalty = self._avoid_penalty(item, intent.avoid_signals, request.avoid)
        score = ((text * 0.34) + (genre * 0.28) + (mood * 0.22) + (quality * 0.11) + (popularity * 0.05) - penalty) * topic
        return max(0, min(1, score))

    def _sort_key(self, item: CatalogItem, score: float, sort: str) -> float:
        if sort == "rating":
            return item.get("weightedRating") or 0
        if sort == "popular":
            return item.get("votes") or 0
        if sort == "recent":
            return item.get("year") or 0
        return score

    def _format_result(self, item: CatalogItem, score: float, intent: Intent, request: RecommendRequest) -> RecommendationResult:
        moods = [facet.get("label") for facet in item.get("facets", {}).get("mood", [])[:3] if facet.get("label")]
        return RecommendationResult(
            id=item.get("id", ""),
            title=item.get("title", ""),
            year=item.get("year"),
            type=item.get("type", ""),
            type_label=label_content_type(item.get("type", "")),
            genres=item.get("genres", []),
            rating=item.get("rating"),
            votes=item.get("votes") or 0,
            description=item.get("description", ""),
            moods=moods,
            poster_url=item.get("posterUrl"),
            match_score=round(score, 4),
            why=self._build_why(item, intent, score),
        )

    def _build_why(self, item: CatalogItem, intent: Intent, score: float) -> str:
        top_mood = ", ".join(facet.get("label", "") for facet in item.get("facets", {}).get("mood", [])[:2] if facet.get("label"))
        top_arc = ", ".join(facet.get("label", "") for facet in item.get("facets", {}).get("arc", [])[:2] if facet.get("label"))
        genre_match = [genre for genre in intent.inferred_genres if genre in item.get("genres", [])]
        pieces = [f"Match score: {round(score * 100)}%."]
        pieces.append(f"Genre intent matched: {', '.join(genre_match)}." if genre_match else "Matched through prompt language, NLP topic, and facets.")
        if top_mood:
            pieces.append(f"Mood signals: {top_mood}.")
        if top_arc:
            pieces.append(f"Emotional arc: {top_arc}.")
        if item.get("topic"):
            pieces.append(f"Topic: {item['topic']}.")
        return " ".join(pieces)


def label_content_type(content_type: str) -> str:
    return {
        "movie": "Movie",
        "tvSeries": "TV series",
        "tvMiniSeries": "TV miniseries",
        "tvMovie": "TV movie",
        "tvEpisode": "TV episode",
        "short": "Short",
        "tvShort": "TV short",
        "tvSpecial": "TV special",
        "video": "Video",
        "videoGame": "Video game",
    }.get(content_type, content_type)
