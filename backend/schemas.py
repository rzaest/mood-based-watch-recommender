from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RecommendRequest(BaseModel):
    prompt: str = Field(default="", max_length=2000)
    type: Literal["all", "movie", "tv", "short"] = "all"
    genre: str = "all"
    mood: str = "all"
    avoid: Literal["none", "dark", "sad", "scary", "violent"] = "none"
    min_rating: float = Field(default=6.5, ge=0, le=10)
    min_votes: int = Field(default=30000, ge=0)
    year_from: int = Field(default=1990, ge=1800, le=2100)
    year_to: int = Field(default=2023, ge=1800, le=2100)
    limit: int = Field(default=12, ge=1, le=50)
    sort: Literal["match", "rating", "popular", "recent"] = "match"

    @field_validator("prompt")
    @classmethod
    def clean_prompt(cls, value: str) -> str:
        return value.strip()


class RecommendationResult(BaseModel):
    id: str
    title: str
    year: int | None = None
    type: str
    type_label: str
    genres: list[str]
    rating: float | None = None
    votes: int = 0
    description: str
    moods: list[str] = []
    poster_url: str | None = None
    match_score: float
    why: str


class RecommendResponse(BaseModel):
    interpreted_request: str
    effective_type: str
    inferred_genres: list[str]
    inferred_moods: list[str]
    avoided_signals: list[str]
    seed_title: str | None = None
    seed_source: str | None = None
    count: int
    message: str | None = None
    results: list[RecommendationResult]


class CatalogSummary(BaseModel):
    total_titles: int
    year_min: int | None
    year_max: int | None
    genres: list[str]
    types: list[str]
    moods: list[str]
    poster_count: int
    source: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    catalog_loaded: bool
    title_count: int = 0
    detail: str | None = None


CatalogItem = dict[str, Any]
