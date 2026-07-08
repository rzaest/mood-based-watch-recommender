import math
import re
import json
import urllib.parse
import urllib.request
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
    "Action": ["action", "fight", "combat", "explosive", "chase", "adrenaline", "battle", "action packed", "high energy"],
    "Adventure": ["adventure", "journey", "quest", "exploration", "fun", "adventurous", "magical"],
    "Animation": ["animated", "animation", "anime", "cartoon", "cute", "adorable"],
    "Biography": ["biography", "biopic", "true story", "real person", "life story"],
    "Comedy": ["funny", "comedy", "comedic", "laugh", "hilarious", "joyful", "joyous", "cheerful", "silly", "smart comedy", "lighthearted", "feel good"],
    "Crime": ["crime", "criminal", "detective", "police", "murder", "heist", "mafia"],
    "Documentary": ["documentary", "true story", "nonfiction", "real life", "educational"],
    "Drama": ["drama", "emotional", "human", "serious", "character", "moving", "tearjerker"],
    "Family": ["family", "kids", "kid", "children", "childrens", "children's", "child friendly", "kid friendly", "family friendly", "wholesome", "safe", "easy to watch", "cute", "adorable", "sweet", "gentle"],
    "Fantasy": ["fantasy", "magic", "magical", "mythical", "kingdom"],
    "Horror": ["horror", "scary", "creepy", "terrifying", "haunted", "zombie", "monster"],
    "Music": ["music", "musician", "band", "concert", "singer"],
    "Musical": ["musical", "singing", "song and dance"],
    "Mystery": ["mystery", "twist", "twists", "clever", "puzzle", "investigation", "mind bending"],
    "Romance": ["romance", "romantic", "love", "relationship", "date night", "cute couple", "sweet romance"],
    "Sci-Fi": ["sci fi", "sci-fi", "scifi", "science fiction", "future", "futuristic", "space", "alien", "robot"],
    "Sport": ["sport", "sports", "athlete", "competition", "football", "basketball"],
    "Thriller": ["thriller", "tense", "intense", "suspense", "dangerous", "edge of my seat", "gripping", "stressful"],
    "War": ["war", "battlefield", "soldier", "military"],
    "Western": ["western", "cowboy", "frontier", "outlaw"],
}

MOOD_LEXICON = {
    "comforting": ["comforting", "cozy", "warm", "gentle", "easy", "safe", "wholesome", "calm", "cute", "adorable", "sweet", "charming", "soft", "soothing", "pleasant", "nice", "heartwarming"],
    "joyful": ["joyful", "joyous", "cheerful", "happy", "bright", "good mood", "feel good", "lighthearted", "cute", "adorable", "fun", "delightful", "upbeat"],
    "funny": ["funny", "comedy", "comedic", "laugh", "hilarious", "silly", "goofy", "playful"],
    "hopeful": ["hopeful", "uplifting", "inspiring", "optimistic", "positive", "motivational", "empowering", "triumphant"],
    "romantic": ["romantic", "romance", "love", "relationship", "flirty", "tender", "passionate", "date night"],
    "tense": ["tense", "intense", "suspense", "thriller", "anxious", "gripping", "stressful", "edge of my seat", "nerve wracking"],
    "dark": ["dark", "disturbing", "grim", "bleak", "violent", "gritty", "serious", "haunting", "mature"],
    "sad": ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief", "melancholy", "bittersweet", "tearjerker", "emotional"],
    "adventurous": ["adventurous", "adventure", "quest", "journey", "exciting", "epic", "sweeping", "exploration"],
    "mind_bending": ["mind bending", "twisty", "surreal", "psychological", "weird", "strange", "trippy", "clever", "smart", "thought provoking"],
}

AVOID_MAP = {
    "dark": ["dark", "disturbing", "grim", "bleak", "violent", "unsettling"],
    "sad": ["sad", "tragic", "heartbreak", "heartbroken", "depressing", "grief"],
    "scary": ["scary", "horror", "creepy", "terrifying", "haunted", "monster", "zombie"],
    "violent": ["violent", "violence", "intense", "tense", "war", "battle", "murder"],
}

PROMPT_STOPWORDS = {
    "anything",
    "can",
    "could",
    "feel",
    "feeling",
    "film",
    "films",
    "find",
    "give",
    "like",
    "looking",
    "me",
    "movie",
    "movies",
    "need",
    "please",
    "recommend",
    "series",
    "show",
    "shows",
    "something",
    "that",
    "thing",
    "things",
    "tonight",
    "watch",
    "want",
    "wants",
    "with",
}

DESCRIPTOR_RULES = [
    {
        "patterns": [
            r"\bcute\b",
            r"\badorable\b",
            r"\bsweet\b",
            r"\bcharming\b",
            r"\bsoft\b",
            r"\bwholesome\b",
            r"\bfeel good\b",
            r"\blighthearted\b",
            r"\bheartwarming\b",
            r"\bdelightful\b",
            r"\bpleasant\b",
        ],
        "genres": {"Family": 0.85, "Animation": 0.55, "Comedy": 0.55, "Romance": 0.5},
        "moods": {"comforting": 1.0, "joyful": 0.85, "funny": 0.45, "romantic": 0.35},
        "avoid": {"dark": 1.0, "scary": 1.0, "violent": 1.0},
    },
    {
        "patterns": [r"\bcozy\b", r"\bwarm\b", r"\bgentle\b", r"\bsoothing\b", r"\bcomforting\b", r"\bnice\b", r"\bcalm\b"],
        "genres": {"Comedy": 0.4, "Romance": 0.35, "Family": 0.3, "Drama": 0.2},
        "moods": {"comforting": 1.0, "joyful": 0.45, "hopeful": 0.3},
        "avoid": {"dark": 1.0, "scary": 1.0, "violent": 1.0, "sad": 0.5},
    },
    {
        "patterns": [r"\bplayful\b", r"\bgoofy\b", r"\bsilly\b", r"\bfun\b", r"\bfunny\b", r"\bhilarious\b", r"\bmake me laugh\b"],
        "genres": {"Comedy": 1.0, "Animation": 0.25, "Family": 0.25, "Romance": 0.2},
        "moods": {"funny": 1.0, "joyful": 0.75, "comforting": 0.25},
        "avoid": {"dark": 0.8, "sad": 0.6},
    },
    {
        "patterns": [
            r"\bchildren'?s\b",
            r"\bchildrens\b",
            r"\bfor children\b",
            r"\bfor kids\b",
            r"\bkids?\b",
            r"\bkid friendly\b",
            r"\bchild friendly\b",
            r"\bfamily friendly\b",
            r"\bfamily movie\b",
            r"\bfamily film\b",
        ],
        "genres": {"Family": 1.0, "Animation": 0.9, "Adventure": 0.45, "Comedy": 0.4},
        "moods": {"comforting": 1.0, "joyful": 0.85, "hopeful": 0.55, "funny": 0.45},
        "avoid": {"dark": 1.0, "scary": 1.0, "violent": 1.0, "sad": 0.6},
    },
    {
        "patterns": [r"\bmagical\b", r"\bfairy tale\b", r"\bfairytale\b", r"\bwonder\b"],
        "genres": {"Fantasy": 0.95, "Adventure": 0.75, "Family": 0.55, "Animation": 0.45},
        "moods": {"joyful": 0.7, "hopeful": 0.7, "adventurous": 0.65, "comforting": 0.4},
        "avoid": {},
    },
    {
        "patterns": [r"\brelaxing\b", r"\bchill\b", r"\bcalming\b", r"\blow stakes\b", r"\beasygoing\b"],
        "genres": {"Comedy": 0.55, "Family": 0.45, "Romance": 0.35},
        "moods": {"comforting": 1.0, "joyful": 0.55},
        "avoid": {"dark": 1.0, "scary": 1.0, "violent": 1.0, "sad": 0.6},
    },
    {
        "patterns": [r"\bromantic\b", r"\bdate night\b", r"\bflirty\b", r"\btender\b", r"\bsweet romance\b", r"\blove story\b"],
        "genres": {"Romance": 1.0, "Comedy": 0.45, "Drama": 0.25},
        "moods": {"romantic": 1.0, "comforting": 0.55, "joyful": 0.45},
        "avoid": {},
    },
    {
        "patterns": [r"\bsad\b", r"\bemotional\b", r"\bcry\b", r"\btearjerker\b", r"\bheartbreaking\b", r"\bmelancholy\b", r"\bbittersweet\b"],
        "genres": {"Drama": 0.9, "Romance": 0.35},
        "moods": {"sad": 1.0, "romantic": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bdramatic\b", r"\bmoving\b", r"\bpowerful\b", r"\bhuman\b", r"\bcharacter driven\b", r"\bserious story\b"],
        "genres": {"Drama": 1.0, "Biography": 0.3, "Romance": 0.2},
        "moods": {"sad": 0.45, "hopeful": 0.25, "romantic": 0.2},
        "avoid": {},
    },
    {
        "patterns": [r"\bdark\b", r"\bgritty\b", r"\bbleak\b", r"\bserious\b", r"\bmature\b", r"\bhaunting\b"],
        "genres": {"Drama": 0.55, "Thriller": 0.45, "Crime": 0.35},
        "moods": {"dark": 1.0, "tense": 0.45, "sad": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bscary\b", r"\bcreepy\b", r"\bhorror\b", r"\bspooky\b", r"\bunsettling\b", r"\bterrifying\b"],
        "genres": {"Horror": 1.0, "Thriller": 0.55, "Mystery": 0.25},
        "moods": {"dark": 0.9, "tense": 0.8, "mind_bending": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bintense\b", r"\btense\b", r"\bgripping\b", r"\bsuspenseful\b", r"\bhigh stakes\b", r"\bedge of my seat\b"],
        "genres": {"Thriller": 0.9, "Action": 0.55, "Crime": 0.35},
        "moods": {"tense": 1.0, "dark": 0.35},
        "avoid": {},
    },
    {
        "patterns": [r"\bmysterious\b", r"\bmystery\b", r"\btwisty\b", r"\bwith twists\b", r"\bpuzzle\b", r"\binvestigation\b"],
        "genres": {"Mystery": 1.0, "Thriller": 0.45, "Crime": 0.35, "Drama": 0.2},
        "moods": {"mind_bending": 0.7, "tense": 0.55},
        "avoid": {},
    },
    {
        "patterns": [r"\bsmart\b", r"\bclever\b", r"\bthought provoking\b", r"\bintellectual\b", r"\bcomplex\b", r"\bmind bending\b"],
        "genres": {"Mystery": 0.75, "Sci-Fi": 0.55, "Drama": 0.25},
        "moods": {"mind_bending": 1.0, "tense": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bweird\b", r"\bstrange\b", r"\bsurreal\b", r"\btrippy\b", r"\boffbeat\b", r"\bquirky\b"],
        "genres": {"Fantasy": 0.45, "Sci-Fi": 0.45, "Comedy": 0.35},
        "moods": {"mind_bending": 1.0, "funny": 0.35},
        "avoid": {},
    },
    {
        "patterns": [r"\binspiring\b", r"\buplifting\b", r"\bmotivational\b", r"\bempowering\b", r"\btriumphant\b"],
        "genres": {"Drama": 0.45, "Biography": 0.4, "Sport": 0.35, "Family": 0.25},
        "moods": {"hopeful": 1.0, "joyful": 0.45, "comforting": 0.35},
        "avoid": {"dark": 0.45, "sad": 0.25},
    },
    {
        "patterns": [r"\bfast paced\b", r"\baction packed\b", r"\bexplosive\b", r"\badrenaline\b", r"\bexciting\b"],
        "genres": {"Action": 1.0, "Adventure": 0.55, "Thriller": 0.35},
        "moods": {"adventurous": 0.85, "tense": 0.45},
        "avoid": {},
    },
    {
        "patterns": [r"\bepic\b", r"\bgrand\b", r"\bbig adventure\b", r"\bquest\b", r"\bjourney\b", r"\bheroic\b"],
        "genres": {"Adventure": 1.0, "Fantasy": 0.45, "Action": 0.35, "Drama": 0.2},
        "moods": {"adventurous": 1.0, "hopeful": 0.35, "tense": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\brealistic\b", r"\beducational\b", r"\binformative\b", r"\btrue story\b", r"\breal life\b", r"\bnonfiction\b"],
        "genres": {"Documentary": 0.95, "Biography": 0.55, "Drama": 0.25},
        "moods": {"hopeful": 0.25, "mind_bending": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bmusical\b", r"\bmusic\b", r"\bsinging\b", r"\bsongs\b", r"\bconcert\b", r"\bdance\b"],
        "genres": {"Music": 0.8, "Musical": 0.8, "Drama": 0.25, "Comedy": 0.2},
        "moods": {"joyful": 0.55, "romantic": 0.25, "hopeful": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bdetective\b", r"\bcrime\b", r"\bheist\b", r"\bmafia\b", r"\bcriminal\b", r"\bpolice\b"],
        "genres": {"Crime": 1.0, "Mystery": 0.45, "Thriller": 0.35, "Drama": 0.25},
        "moods": {"tense": 0.65, "dark": 0.35},
        "avoid": {},
    },
    {
        "patterns": [r"\bfuturistic\b", r"\bspace\b", r"\balien\b", r"\brobot\b", r"\bsci fi\b", r"\bscience fiction\b"],
        "genres": {"Sci-Fi": 1.0, "Adventure": 0.35, "Action": 0.3, "Mystery": 0.2},
        "moods": {"mind_bending": 0.55, "adventurous": 0.35, "tense": 0.25},
        "avoid": {},
    },
    {
        "patterns": [r"\bnostalgic\b", r"\bclassic\b", r"\bold school\b", r"\bretro\b"],
        "genres": {"Drama": 0.3, "Comedy": 0.25, "Family": 0.25},
        "moods": {"comforting": 0.55, "joyful": 0.35, "sad": 0.2},
        "avoid": {},
    },
]

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
    seed_query: str | None = None
    wants_similarity: bool = False
    family_safe: bool = False
    child_safe: bool = False
    excluded_genres: set[str] | None = None


@dataclass
class SeedMatch:
    title: str
    source: str
    item: CatalogItem | None = None
    metadata: dict[str, Any] | None = None


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


def normalize_title(text: str | None) -> str:
    value = normalize(text)
    value = re.sub(r"\b(the|a|an)\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def extract_seed_query(text: str) -> tuple[str | None, bool]:
    patterns = [
        (r"\b(?:something|films?|movies?|shows?|series)?\s*(?:like|similar to|close to)\s+(.+)$", True),
        (r"\b(?:based on|in the style of)\s+(.+)$", True),
        (r"\b(?:watch|see|find|recommend|show me)\s+(.+)$", False),
    ]
    cleanup = r"\b(?:but|and|with|without|that is|that are|please|tonight|right now)\b"
    for pattern, wants_similarity in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = re.split(cleanup, match.group(1))[0].strip(" '\"")
        candidate = re.sub(r"\b(movie|film|show|series|tv)\b", " ", candidate).strip()
        if candidate and len(candidate.split()) <= 8:
            return candidate, wants_similarity
    return None, False


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


def infer_excluded_genres(text: str) -> set[str]:
    excluded: set[str] = set()
    for genre, phrases in GENRE_LEXICON.items():
        candidates = {genre.lower(), genre.lower().replace("-", " "), *phrases}
        for phrase in candidates:
            if phrase_negated(text, normalize(phrase)):
                excluded.add(genre)
                break
    if re.search(r"\b(no|not|without|avoid|exclude)\s+(cartoon|cartoons|animated|animation|anime)\b", text):
        excluded.add("Animation")
    if re.search(r"\b(no|not|without|avoid|exclude)\s+(love story|love stories|romcom|rom com|romance|romantic)\b", text):
        excluded.add("Romance")
    return excluded


def apply_descriptor_rules(text: str, inferred_genres: dict[str, float], inferred_moods: dict[str, float], avoid_signals: dict[str, float]) -> None:
    for rule in DESCRIPTOR_RULES:
        if not any(re.search(pattern, text) for pattern in rule["patterns"]):
            continue
        for genre, weight in rule["genres"].items():
            inferred_genres[genre] = max(inferred_genres.get(genre, 0), weight)
        for mood, weight in rule["moods"].items():
            inferred_moods[mood] = max(inferred_moods.get(mood, 0), weight)
        for avoid, weight in rule["avoid"].items():
            avoid_signals[avoid] = max(avoid_signals.get(avoid, 0), weight)


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
    excluded_genres = infer_excluded_genres(text)
    seed_query, wants_similarity = extract_seed_query(text)
    apply_descriptor_rules(text, inferred_genres, inferred_moods, avoid_signals)
    for genre in excluded_genres:
        inferred_genres.pop(genre, None)
    family_safe = re.search(
        r"\b(cute|adorable|sweet|wholesome|children'?s|childrens|for children|for kids|kids?|kid friendly|child friendly|family friendly|family movie|family film)\b",
        text,
    ) is not None
    child_safe = re.search(
        r"\b(children'?s|childrens|for children|for kids|kids?|kid friendly|child friendly|family friendly|family movie|family film)\b",
        text,
    ) is not None

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

    return Intent(
        text,
        desired_text,
        inferred_genres,
        inferred_moods,
        avoid_signals,
        detect_type_from_prompt(text),
        seed_query,
        wants_similarity,
        family_safe,
        child_safe,
        excluded_genres,
    )


class MoodRecommender:
    def __init__(self, catalog: dict[str, Any]):
        self.meta = catalog["meta"]
        self.items: list[CatalogItem] = catalog["items"]
        self.title_index = [(normalize_title(item.get("title")), item) for item in self.items]

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
        seed = self._resolve_seed(intent.seed_query) if intent.seed_query else None
        if seed and seed.item and not intent.type_from_prompt:
            if seed.item.get("type") == "movie":
                effective_type = "movie"
            elif seed.item.get("type") in TYPE_GROUPS["tv"]:
                effective_type = "tv"
        elif seed and seed.metadata and not intent.type_from_prompt:
            if seed.metadata.get("kind") == "movie":
                effective_type = "movie"
            elif seed.metadata.get("kind") == "tv":
                effective_type = "tv"
        merged_moods = dict(intent.inferred_moods)
        if request.mood != "all":
            merged_moods[request.mood] = 1
        intent = Intent(
            intent.text,
            intent.desired_text,
            intent.inferred_genres,
            merged_moods,
            intent.avoid_signals,
            intent.type_from_prompt,
            intent.seed_query,
            intent.wants_similarity,
            intent.family_safe,
            intent.child_safe,
            intent.excluded_genres,
        )

        scored: list[tuple[CatalogItem, float]] = []
        for item in self.items:
            if not self._type_matches(item, effective_type):
                continue
            if intent.excluded_genres and set(item.get("genres", [])) & intent.excluded_genres:
                continue
            if seed and intent.wants_similarity and seed.item and item.get("id") == seed.item.get("id"):
                continue
            if (item.get("rating") or 0) < request.min_rating:
                continue
            if (item.get("votes") or 0) < request.min_votes:
                continue
            year = item.get("year") or 0
            if year < request.year_from or year > request.year_to:
                continue
            score = self._score_item(item, intent, request, seed)
            if score > 0.05:
                scored.append((item, score))

        scored.sort(key=lambda row: self._sort_key(row[0], row[1], request.sort), reverse=True)
        raw_results = scored[: request.limit]
        display_scores = self._calibrate_scores([score for _, score in raw_results])
        results = [
            self._format_result(item, raw_score, display_score, intent, request, seed)
            for (item, raw_score), display_score in zip(raw_results, display_scores, strict=False)
        ]
        avoids = sorted(
            set(([request.avoid] if request.avoid != "none" else []) + list(intent.avoid_signals) + list(intent.excluded_genres or []))
        )

        return RecommendResponse(
            interpreted_request=intent.desired_text or "No prompt text",
            effective_type=effective_type,
            inferred_genres=list(intent.inferred_genres),
            inferred_moods=list(intent.inferred_moods),
            avoided_signals=avoids,
            seed_title=seed.title if seed else None,
            seed_source=seed.source if seed else None,
            count=len(results),
            message=None if results else "No matches passed the filters. Try lowering the vote/rating threshold or widening the format selector.",
            results=results,
        )

    def _resolve_seed(self, seed_query: str | None) -> SeedMatch | None:
        if not seed_query:
            return None
        local = self._find_catalog_seed(seed_query)
        if local:
            return SeedMatch(title=local.get("title", seed_query), source="catalog", item=local)
        external = self._lookup_external_seed(seed_query)
        if external:
            return SeedMatch(title=external["title"], source="imdb_suggestion", metadata=external)
        return None

    def _find_catalog_seed(self, seed_query: str) -> CatalogItem | None:
        query = normalize_title(seed_query)
        if not query:
            return None
        query_tokens = set(query.split())
        best_item = None
        best_score = 0.0
        for title, item in self.title_index:
            title_tokens = set(title.split())
            if not title_tokens:
                continue
            overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
            contains = 0.35 if query in title or title in query else 0
            starts = 0.15 if title.startswith(query) else 0
            popularity = min(1, math.log10((item.get("votes") or 0) + 1) / 6.5) * 0.1
            quality = min(1, (item.get("weightedRating") or item.get("rating") or 0) / 9.2) * 0.05
            score = overlap + contains + starts + popularity + quality
            if score > best_score:
                best_score = score
                best_item = item
        return best_item if best_score >= 0.48 else None

    def _lookup_external_seed(self, seed_query: str) -> dict[str, Any] | None:
        slug = re.sub(r"[^a-z0-9]+", "_", normalize(seed_query)).strip("_")
        if not slug:
            return None
        url = f"https://v2.sg.media-imdb.com/suggestion/{slug[0]}/{urllib.parse.quote(slug)}.json"
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, json.JSONDecodeError):
            return None
        for candidate in payload.get("d", []):
            title = candidate.get("l")
            if not title:
                continue
            qid = candidate.get("qid") or candidate.get("q")
            kind = "movie" if qid in {"movie", "feature"} else "tv" if qid in {"tvSeries", "tvMiniSeries", "tvMovie"} else None
            image = candidate.get("i") or {}
            return {
                "title": title,
                "year": candidate.get("y"),
                "kind": kind,
                "id": candidate.get("id"),
                "poster_url": image.get("imageUrl"),
                "credits": candidate.get("s"),
                "query": seed_query,
            }
        return None

    def _type_matches(self, item: CatalogItem, type_filter: str) -> bool:
        if type_filter == "all":
            return True
        return item.get("type") in TYPE_GROUPS.get(type_filter, set())

    def _facet_score(self, item: CatalogItem, category: str, wanted: dict[str, float]) -> float:
        facets = item.get("facets", {}).get(category, [])
        return sum(wanted.get(facet.get("label"), 0) * max(float(facet.get("score") or 0), 0.08) for facet in facets)

    def _text_score(self, item: CatalogItem, intent: Intent) -> float:
        tokens = [token for token in intent.desired_text.split() if len(token) > 3 and token not in PROMPT_STOPWORDS]
        if not tokens:
            return 0
        search_tokens = set(normalize(item.get("searchText", "")).split())
        hits = sum(1 for token in tokens if token in search_tokens)
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

    def _family_safety_adjustment(self, item: CatalogItem, intent: Intent) -> float:
        if not intent.family_safe:
            return 0
        genres = set(item.get("genres", []))
        facets = {facet.get("label") for group in item.get("facets", {}).values() for facet in group}
        score = 0.0
        if not intent.child_safe:
            if genres & {"Family", "Animation", "Comedy", "Romance"}:
                score += 0.12
            if not genres & {"Family", "Animation", "Romance"}:
                score -= 0.18
            if facets & {"whimsical", "sincere", "love", "home_family", "escapist", "uplifting"}:
                score += 0.08
            if genres & {"Crime", "Horror", "War"}:
                score -= 0.22
            if genres & {"Thriller"}:
                score -= 0.1
            if facets & {"dark", "violent", "bleak", "unsettling", "criminal", "gritty", "tragic", "revenge", "survival"}:
                score -= 0.18
            if facets & {"satirical", "suspenseful"}:
                score -= 0.08
            return score
        if genres & {"Family", "Animation"}:
            score += 0.22
        if genres & {"Adventure", "Comedy", "Fantasy"}:
            score += 0.06
        if not genres & {"Family", "Animation"}:
            score -= 0.34
        if genres & {"Crime", "Horror", "Thriller", "War"}:
            score -= 0.28
        if facets & {"dark", "violent", "bleak", "unsettling", "criminal", "gritty", "tragic", "revenge", "survival"}:
            score -= 0.16
        return score

    def _seed_similarity(self, item: CatalogItem, seed: SeedMatch | None) -> float:
        if not seed:
            return 0
        if seed.item:
            genre_overlap = jaccard(set(item.get("genres", [])), set(seed.item.get("genres", [])))
            topic_match = 1 if item.get("topic") and item.get("topic") == seed.item.get("topic") else 0
            mood_overlap = jaccard(facet_labels(item, "mood"), facet_labels(seed.item, "mood"))
            arc_overlap = jaccard(facet_labels(item, "arc"), facet_labels(seed.item, "arc"))
            setting_overlap = jaccard(facet_labels(item, "setting"), facet_labels(seed.item, "setting"))
            text_overlap = token_overlap(item.get("searchText", ""), seed.item.get("searchText", ""))
            return min(1, genre_overlap * 0.35 + topic_match * 0.22 + mood_overlap * 0.14 + arc_overlap * 0.1 + setting_overlap * 0.08 + text_overlap * 0.11)
        if seed.metadata:
            seed_text = normalize(" ".join(str(seed.metadata.get(key) or "") for key in ["title", "credits", "query"]))
            return min(1, token_overlap(item.get("searchText", ""), seed_text) * 0.75 + self._text_score(item, Intent(seed_text, seed_text, {}, {}, {}, None)) * 0.25)
        return 0

    def _score_item(self, item: CatalogItem, intent: Intent, request: RecommendRequest, seed: SeedMatch | None = None) -> float:
        genre = self._genre_score(item, intent.inferred_genres, request.genre)
        mood = self._facet_score(item, "mood", intent.inferred_moods) + self._facet_score(item, "arc", intent.inferred_moods)
        text = self._text_score(item, intent)
        seed_similarity = self._seed_similarity(item, seed)
        quality = min(1, (item.get("weightedRating") or item.get("rating") or 0) / 9.2)
        popularity = min(1, math.log10((item.get("votes") or 0) + 1) / 6.5)
        topic = 0.82 if item.get("lowConfidence") else 1
        penalty = self._avoid_penalty(item, intent.avoid_signals, request.avoid)
        family_adjustment = self._family_safety_adjustment(item, intent)
        if seed:
            score = ((seed_similarity * 0.52) + (genre * 0.16) + (text * 0.11) + (mood * 0.08) + (quality * 0.08) + (popularity * 0.05) + family_adjustment - penalty) * topic
        else:
            score = ((text * 0.34) + (genre * 0.28) + (mood * 0.22) + (quality * 0.11) + (popularity * 0.05) + family_adjustment - penalty) * topic
        return max(0, min(1, score))

    def _calibrate_scores(self, raw_scores: list[float]) -> list[float]:
        if not raw_scores:
            return []
        best = max(raw_scores)
        if best <= 0:
            return raw_scores
        calibrated = []
        for score in raw_scores:
            relative = score / best
            display = 0.62 + relative * 0.35
            if score < 0.18:
                display = min(display, 0.72)
            calibrated.append(round(max(0, min(0.98, display)), 4))
        return calibrated

    def _sort_key(self, item: CatalogItem, score: float, sort: str) -> float:
        if sort == "rating":
            return item.get("weightedRating") or 0
        if sort == "popular":
            return item.get("votes") or 0
        if sort == "recent":
            return item.get("year") or 0
        return score

    def _format_result(self, item: CatalogItem, raw_score: float, display_score: float, intent: Intent, request: RecommendRequest, seed: SeedMatch | None = None) -> RecommendationResult:
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
            description=plot_description(item.get("description", ""), item.get("title", "")),
            moods=moods,
            poster_url=item.get("posterUrl"),
            match_score=display_score,
            why=self._build_why(item, intent, display_score, seed),
        )

    def _build_why(self, item: CatalogItem, intent: Intent, score: float, seed: SeedMatch | None = None) -> str:
        top_moods = [clean_label(facet.get("label", "")) for facet in item.get("facets", {}).get("mood", [])[:2] if facet.get("label")]
        avoid_dark_or_sad = bool({"dark", "sad", "scary"} & set(intent.avoid_signals))
        top_arcs = [
            clean_label(facet.get("label", ""))
            for facet in item.get("facets", {}).get("arc", [])
            if facet.get("label") and (not avoid_dark_or_sad or facet.get("label") not in {"tragic", "bittersweet", "bleak"})
        ][:2]
        genre_match = [genre for genre in intent.inferred_genres if genre in item.get("genres", [])]
        title = item.get("title", "This title")

        if seed:
            intro = f"{title} is recommended because it shares story style, genre, and tone with {seed.title}."
        elif genre_match:
            intro = f"{title} fits because it lines up with your request for {human_join(genre_match)}."
        else:
            intro = f"{title} fits the feeling of your prompt through its story, tone, and overall mood."

        details = []
        if top_moods:
            details.append(f"It leans {human_join(top_moods)}")
        if top_arcs:
            details.append(f"with an overall {human_join(top_arcs)} story feel")

        if details:
            explanation = intro + " " + ", ".join(details) + "."
        else:
            explanation = intro

        if intent.avoid_signals or intent.excluded_genres:
            explanation += " It also stays away from the main things you said you did not want."
        return explanation


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


def clean_label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def human_join(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def plot_description(description: str, title: str = "") -> str:
    text = re.sub(r"\s+", " ", str(description or "")).strip()
    if not text:
        return ""

    sentences = split_sentences(text)
    kept: list[str] = []
    fallback: list[str] = []

    for sentence in sentences:
        cleaned = clean_plot_sentence(sentence, title)
        if not cleaned:
            continue
        if is_plot_sentence(cleaned):
            kept.append(cleaned)
        elif not is_metadata_sentence(cleaned):
            fallback.append(cleaned)

    chosen = kept or fallback
    if not chosen:
        return truncate_description(text)
    return truncate_description(" ".join(chosen[:3]))


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def clean_plot_sentence(sentence: str, title: str = "") -> str:
    sentence = sentence.strip()
    if not sentence or sentence.endswith("..."):
        return ""
    lowered = sentence.lower()
    title_lower = str(title or "").lower()

    if "classified within" in lowered or "verified genre profile" in lowered:
        return ""
    if title_lower and lowered.startswith(title_lower) and re.search(r"\bis a \d{4}\b|\bis an? \d{4}\b", lowered):
        if not re.search(r"\bfollows\b|\bcenters on\b|\brevolves around\b|\btells\b|\babout\b", lowered):
            return ""

    starring_match = re.search(r"\bstars? .+? as ([^.]+)", sentence, flags=re.IGNORECASE)
    if starring_match and re.search(r"\bwho\b|\bwhose\b|\bmust\b|\btries\b|\bdiscovers\b|\bfinds\b", starring_match.group(1), flags=re.IGNORECASE):
        sentence = starring_match.group(1).strip()

    sentence = re.sub(r",\s+who\s+", " ", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r",\s+whose\s+", " whose ", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"^the storyline follows\b", "The story follows", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"^it follows\b", "The story follows", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"^follows\b", "The story follows", sentence, flags=re.IGNORECASE)
    return sentence[:1].upper() + sentence[1:] if sentence else ""


def is_metadata_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    metadata_patterns = [
        r"\bdirected by\b",
        r"\bwritten by\b",
        r"\bproduced by\b",
        r"\bstarring\b",
        r"\bstars\b",
        r"\breleased\b",
        r"\bpremiered\b",
        r"\baired\b",
        r"\bavailable for streaming\b",
        r"\bbox office\b",
        r"\bfilm festival\b",
        r"\bdvd\b",
        r"\bblu-ray\b",
        r"\bclassified within\b",
        r"\bverified genre profile\b",
    ]
    return any(re.search(pattern, lowered) for pattern in metadata_patterns)


def is_plot_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    plot_patterns = [
        r"\bfollows\b",
        r"\bstory follows\b",
        r"\bcenters on\b",
        r"\bcentres on\b",
        r"\brevolves around\b",
        r"\btells the story\b",
        r"\babout\b",
        r"\bwhen\b",
        r"\bafter\b",
        r"\bwhile\b",
        r"\bmust\b",
        r"\btries to\b",
        r"\bdiscovers\b",
        r"\bfinds\b",
        r"\bsets out\b",
        r"\btravels\b",
        r"\bbecomes\b",
        r"\bstruggles\b",
        r"\bfaces\b",
        r"\buncovers\b",
    ]
    return any(re.search(pattern, lowered) for pattern in plot_patterns)


def truncate_description(text: str, limit: int = 560) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return ensure_sentence_end(text)
    truncated = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}..."


def ensure_sentence_end(text: str) -> str:
    return text if not text or text[-1] in ".!?" else f"{text}."


def facet_labels(item: CatalogItem, category: str) -> set[str]:
    return {facet.get("label", "") for facet in item.get("facets", {}).get(category, []) if facet.get("label")}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0
    return len(left & right) / len(left | right)


def token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in normalize(left).split() if len(token) > 3}
    right_tokens = {token for token in normalize(right).split() if len(token) > 3}
    return jaccard(left_tokens, right_tokens)
