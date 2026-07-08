import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .data_loader import CatalogLoadError, PROJECT_ROOT, load_catalog
from .recommender import MoodRecommender
from .schemas import CatalogSummary, HealthResponse, RecommendRequest, RecommendResponse


FRONTEND_ROOT = PROJECT_ROOT
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8765,http://127.0.0.1:8765",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Mood-Based Watch Recommender API",
    version="1.0.0",
    description="Backend API for prompt-aware movie and TV recommendations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

recommender: MoodRecommender | None = None
catalog_error: str | None = None


@app.on_event("startup")
def startup() -> None:
    global recommender, catalog_error
    try:
        recommender = MoodRecommender(load_catalog())
        catalog_error = None
    except CatalogLoadError as exc:
        recommender = None
        catalog_error = str(exc)


def require_recommender() -> MoodRecommender:
    if recommender is None:
        raise HTTPException(status_code=503, detail=catalog_error or "Catalog is not loaded.")
    return recommender


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if recommender is None:
        return HealthResponse(status="error", catalog_loaded=False, detail=catalog_error)
    return HealthResponse(status="ok", catalog_loaded=True, title_count=len(recommender.items))


@app.get("/catalog/summary", response_model=CatalogSummary)
def catalog_summary() -> CatalogSummary:
    return require_recommender().summary()


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        return require_recommender().recommend(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "app.js", media_type="application/javascript")


@app.get("/config.js")
def config_js() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "config.js", media_type="application/javascript")


@app.get("/styles.css")
def styles_css() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "styles.css", media_type="text/css")


@app.get("/assets/data/catalog.json")
def catalog_artifact() -> FileResponse:
    # Kept available for inspection/download; recommendations use the backend API.
    return FileResponse(FRONTEND_ROOT / "assets" / "data" / "catalog.json", media_type="application/json")


@app.get("/{path:path}")
def frontend_fallback(path: str) -> FileResponse:
    candidate = (FRONTEND_ROOT / path).resolve()
    if candidate.is_file() and PROJECT_ROOT in candidate.parents:
        return FileResponse(candidate)
    index_path = Path(FRONTEND_ROOT / "index.html")
    return FileResponse(index_path)
