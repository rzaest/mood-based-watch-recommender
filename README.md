# Mood-Based Watch Recommender

A backend-connected mood-aware movie and TV recommendation app. The frontend collects a user's prompt and filters, calls a FastAPI backend, and renders ranked recommendations from the final NLP catalog created by the project notebooks.

## Current Architecture

This is no longer a frontend-only static recommender.

- `backend/main.py` exposes the API and can also serve the frontend.
- `backend/recommender.py` contains prompt parsing, format detection, filtering, scoring, avoid-signal handling, and recommendation explanations.
- `backend/data_loader.py` loads and validates the deployable catalog.
- `backend/schemas.py` defines request and response models.
- `backend/build_catalog.py` rebuilds `assets/data/catalog.json` from `data/final_nlp_recommender_features.csv` when needed.
- `app.js` only calls the backend API and renders the response.
- `assets/data/catalog.json` is the production data artifact generated from the final NLP feature table.

## API Endpoints

- `GET /health`
  Returns backend status and whether the catalog loaded.

- `GET /catalog/summary`
  Returns title count, year range, genres, content types, moods, poster count, and source file.

- `POST /recommend`
  Accepts prompt/filter JSON and returns interpreted request details plus ranked recommendation results.

Example request:

```json
{
  "prompt": "I feel sad and want something funny and comforting",
  "type": "all",
  "genre": "all",
  "mood": "all",
  "avoid": "scary",
  "min_rating": 6.5,
  "min_votes": 30000,
  "year_from": 1990,
  "year_to": 2023,
  "limit": 12,
  "sort": "match"
}
```

## Run Locally

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the app:

```text
http://127.0.0.1:8000
```

The backend serves `index.html`, `styles.css`, `config.js`, and `app.js`, so the frontend and API work from the same origin.

Optional separate frontend mode:

```bash
python -m http.server 8765
```

Then open `http://127.0.0.1:8765`. In that mode, `app.js` automatically calls `http://localhost:8000`.

## Deployment

Recommended: deploy as one full-stack Render web service.

Render settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Environment variable: `ALLOWED_ORIGINS`
  - For same-origin Render deployment, the default is usually enough.
  - For a separate frontend, include the frontend origin, for example `https://your-site.netlify.app`.

This repo includes `render.yaml` as a Render blueprint.

Netlify-only deployment is no longer the recommended setup because recommendations now require the FastAPI backend. If you deploy the frontend separately on Netlify, deploy the backend on Render/Railway and set `window.MBWR_API_BASE_URL` in `config.js` to the backend URL.

## Product Features

- Natural-language prompts such as `I feel sad and heartbroken and I want to watch something joyous and comedic`.
- Backend-side prompt interpretation and recommendation scoring.
- Automatic format detection. If the prompt asks for a movie/film, only movies are returned. If it asks for TV/show/series, TV formats are returned.
- Genre, mood, avoid-signal, rating, vote, year, result-count, and sorting controls.
- Avoid handling for prompts such as `not scary`, `not sad`, `no crime`, `no heavy drama`, or `please do not destroy me`.
- Current-emotion vs desired-content handling, so `I feel sad... I want something joyous and comedic` avoids sad/dark signals.
- Poster/cover URLs for all 7,848 catalog titles.

## Model And Notebook Files

The main modeling notebook is:

- `01_bertopic_nlp_pipeline.ipynb`

It contains the final NLP pipeline, including sentence-embedding semantic features, topic assignment, human-readable topic labels, low-confidence topic flags, weighted emotional facets, prompt intent parsing, and stress tests.

Additional notebooks kept for project explanation:

- `02_phase2_plot_enrichment.ipynb`
- `03_extensive_description_rebuild.ipynb`
- `04_batch_wikipedia_extract_fallback_enrichment.ipynb`
- `05_finalize_training_descriptions.ipynb`
- `watch.ipynb`

Useful final review files:

- `data/bertopic_topic_review.csv`
- `data/prompt_recommendation_stress_summary.csv`
- `data/prompt_recommendation_evaluation.csv`

Presentation files:

- `presentation.qmd`
- `presentation.html`
- `presentation.css`
- `output/pdf/mood_based_watch_recommender_presentation.pdf`

## Data Artifact

The backend does not run notebooks in production. It loads:

```text
assets/data/catalog.json
```

To rebuild it from the final feature table:

```bash
python backend/build_catalog.py
```

The source table is:

```text
data/final_nlp_recommender_features.csv
```

## What Is Not Included

The old `rule_based_recommender.ipynb` and `content_based_recommender.ipynb` notebooks are intentionally not part of the final deliverable because the backend recommender replaced them.

The local Python virtual environment and trained model directory are excluded from GitHub.
