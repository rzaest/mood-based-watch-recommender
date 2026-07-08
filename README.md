# Mood-Based Watch Recommender

A prompt-aware movie and TV recommendation system built from the final NLP catalog. The product has a minimal web interface, a FastAPI backend, poster-backed recommendation cards, prompt understanding, filters, and interpretable match explanations.

## What To Open First

- Web app: run the backend and open `http://127.0.0.1:8000`
- Main project notebook: `01_bertopic_nlp_pipeline.ipynb`
- Presentation source: `presentation.qmd`
- Rendered presentation: `presentation.html`
- PDF slides: `output/pdf/mood_based_watch_recommender_presentation.pdf`

## Final Product Architecture

This is a backend-connected app, not a static-only recommender.

- `backend/main.py` serves the API and the frontend files.
- `backend/recommender.py` handles prompt parsing, title matching, exclusions, filters, scoring, and explanations.
- `backend/data_loader.py` validates and loads the production catalog.
- `backend/schemas.py` defines the request and response models.
- `assets/data/catalog.json` is the production runtime catalog used by the backend.
- `index.html`, `styles.css`, `app.js`, and `config.js` are the frontend.
- `netlify.toml` is for hosting the frontend on Netlify.
- `render.yaml` is for deploying the FastAPI backend on Render.

## Run Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
```

Start the app:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Health checks:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/catalog/summary
```

## Recommendation Features

- Natural language prompts such as `I feel sad and heartbroken and I want something joyous and comedic`.
- Format detection: prompts asking for a movie return movies; prompts asking for a show or series return TV formats.
- Title-seed matching for prompts like `I want something like The Terminator`.
- Genre, mood, avoid, rating, vote, year, result count, and sort controls.
- Hard exclusions for obvious wording such as `no animation`, `not horror`, `without romance`, or `no drama`.
- Broader descriptor support for everyday language such as cute, cozy, comforting, playful, romantic, dark, tense, mysterious, weird, thought-provoking, uplifting, action-packed, epic, educational, musical, crime, sci-fi, nostalgic, and children/family-friendly.
- Separate handling for cute/soft prompts versus children/family-safe prompts.
- Calibrated match percentages so clear top matches display as strong matches.
- Poster images for catalog titles through IMDb-id poster URLs.

## Important Data And Notebook Files

The backend does not run notebooks in production. It loads:

```text
assets/data/catalog.json
```

The catalog was built from:

```text
data/final_nlp_recommender_features.csv
```

That source CSV is intentionally ignored by Git because the production artifact is already included.

Kept final review CSV files:

- `data/bertopic_topic_review.csv`
- `data/prompt_recommendation_evaluation.csv`
- `data/prompt_recommendation_stress_summary.csv`

Kept notebooks:

- `01_bertopic_nlp_pipeline.ipynb`
- `02_phase2_plot_enrichment.ipynb`
- `03_extensive_description_rebuild.ipynb`
- `04_batch_wikipedia_extract_fallback_enrichment.ipynb`
- `05_finalize_training_descriptions.ipynb`
- `watch.ipynb`

Old rule-based and content-based recommender notebooks are not included in the final pushed deliverable because the FastAPI recommender replaced them.

## Rebuild The Catalog

Only needed if the final NLP feature CSV changes:

```bash
python backend/build_catalog.py
```

`backend/build_catalog.py` requires `pandas`. The deployed app does not rebuild the catalog during normal requests.

## Deployment Overview

Netlify hosts static frontend files. It does not run the FastAPI backend by itself. For the final product, deploy two pieces:

- Backend API on Render, Railway, or another Python web-service host.
- Frontend on Netlify, pointed at the backend API URL.

The easiest full-stack deployment is Render only, because `backend/main.py` can serve both the API and frontend from one service.

## Deploy Backend On Render

Use this repository on Render as a Web Service.

Recommended settings:

- Build command: `pip install -r requirements-backend.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

Set `ALLOWED_ORIGINS` after you know your Netlify URL:

```text
https://your-netlify-site.netlify.app,http://localhost:8000,http://localhost:8765,http://127.0.0.1:8765
```

This repo also includes `render.yaml`, which uses the lighter backend requirements file.

## Connect Netlify To The Backend

1. Deploy the backend first and copy its public URL, for example:

```text
https://mood-based-watch-recommender.onrender.com
```

2. In `config.js`, set:

```js
window.MBWR_API_BASE_URL = "https://mood-based-watch-recommender.onrender.com";
```

3. Commit and push that change, or set it before your final Netlify deployment.

4. In Netlify, choose this GitHub repo.

5. Use these Netlify settings:

```text
Build command: leave empty
Publish directory: .
```

6. After Netlify gives you the site URL, add that URL to the backend `ALLOWED_ORIGINS` value and redeploy/restart the backend.

7. Test the Netlify site by opening the browser console and confirming calls to:

```text
https://your-backend-url/recommend
```

If `config.js` is left empty, the frontend expects the API to be on the same origin. That works when FastAPI serves the frontend locally or on Render, but not for a separate Netlify frontend.

## Cleanup Notes

- `.venv`, model folders, raw exports, large intermediate CSVs, and NumPy embedding files are ignored by Git.
- The pushed repository keeps the final app, backend, catalog artifact, notebooks, presentation files, and final review CSVs.
- `requirements-backend.txt` is for deployment.
- `requirements.txt` is kept for notebook/modeling reproducibility.
