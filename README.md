# Mood-Based Watch Recommender

Live frontend: https://mood-based-watch-recommender.netlify.app
Backend API: https://mood-based-watch-recommender.onrender.com

Mood-Based Watch Recommender is a movie and TV recommendation product that lets users describe what they want to watch in natural language. Instead of only choosing a genre, the user can write prompts such as:

- `I feel sad and heartbroken and I want something joyous and comedic`
- `I want something cute but not animation`
- `I want a children's movie`
- `I want something like The Terminator`
- `I want something weird and thought-provoking but not horror`

The system reads the prompt, applies format and filter controls, excludes clearly unwanted genres or moods, and returns ranked recommendations with posters, match percentages, metadata, and short explanations.

## Product Walkthrough

The website has three main parts:

1. Prompt search
   The user writes what they feel like watching. The backend interprets descriptors, genres, exclusions, title references, and format requests.

2. Filters
   Users can narrow the catalog by format, genre, mood, rating, vote count, year range, result count, and sorting method.

3. Recommendation cards
   Results include poster image, title, year, format, genres, rating, vote count, match percentage, description, and a concise reason for the match.

If a prompt asks specifically for a movie, the backend returns movies. If it asks for a show, series, or TV, the backend returns TV formats. If the prompt says `no animation`, `not horror`, `without romance`, or `no drama`, those genres are hard-excluded from the result set.

## How The System Works

The final app is backend-connected. Netlify hosts the frontend, and Render hosts the FastAPI backend.

Runtime flow:

1. `index.html`, `styles.css`, `config.js`, and `app.js` load in the browser.
2. `config.js` points the deployed Netlify frontend to the Render backend.
3. The frontend sends prompt/filter JSON to `POST /recommend`.
4. `backend/main.py` receives the request.
5. `backend/recommender.py` parses intent, detects format, applies exclusions, scores titles, calibrates match percentages, and returns recommendations.
6. The frontend renders the returned recommendation cards.

The deployed backend does not run notebooks at request time. It loads the production catalog:

```text
assets/data/catalog.json
```

That catalog is built from the final NLP feature table created in the notebooks.

## Main Files

- `index.html` - frontend layout
- `styles.css` - frontend styling
- `app.js` - frontend behavior and API calls
- `config.js` - deployed frontend API URL configuration
- `backend/main.py` - FastAPI app, API routes, and static frontend serving
- `backend/recommender.py` - prompt parsing, title matching, filtering, scoring, exclusions, and explanations
- `backend/data_loader.py` - production catalog validation/loading
- `backend/build_catalog.py` - converts the final NLP feature table into `assets/data/catalog.json`
- `backend/schemas.py` - request/response models
- `assets/data/catalog.json` - deployable recommendation catalog
- `render.yaml` - Render backend deployment blueprint
- `netlify.toml` - Netlify frontend hosting config
- `requirements-backend.txt` - lightweight backend deployment dependencies
- `requirements.txt` - full notebook/modeling environment for reproducibility

## Notebooks Included

The notebooks are included because they explain the data, enrichment, topic, label, facet, and evaluation work behind the final product.

- `watch.ipynb`
  Cleans the original IMDb export, audits missing or mismatched descriptions, applies verified fills, removes unusable rows, and prepares the first recommender-ready dataset.

- `02_phase2_plot_enrichment.ipynb`
  Enriches weak descriptions with source-grounded plot/premise text using IMDb `tconst -> Wikidata P345 -> English Wikipedia`.

- `03_extensive_description_rebuild.ipynb`
  Rebuilds the modeling text layer, audits suspicious descriptions, and reduces title-description mismatch risk.

- `04_batch_wikipedia_extract_fallback_enrichment.ipynb`
  Completes dataset-scale enrichment using batched Wikipedia extracts matched through verified identifiers.

- `05_finalize_training_descriptions.ipynb`
  Finalizes the training descriptions and uses no-hallucination metadata expansion when source-grounded plot text is unavailable.

- `01_bertopic_nlp_pipeline.ipynb`
  Main NLP pipeline. It builds sentence-embedding features, topic labels, low-confidence topic flags, weighted facets, prompt stress tests, and the final feature table used by the backend catalog.

## Recommendation Intelligence

The recommender combines several signals instead of relying on one keyword match:

- requested format from prompt or UI
- explicit genre and mood filters
- inferred genres from natural language
- inferred moods and emotional descriptors
- hard-excluded genres from phrases like `no romance` or `not horror`
- title-seed similarity for prompts like `something like The Terminator`
- weighted facets for mood, tone, theme, conflict, pace, emotional arc, and setting
- rating and vote thresholds
- calibrated match percentages

The descriptor vocabulary supports common user language including cute, cozy, comforting, playful, romantic, dark, tense, mysterious, weird, thought-provoking, uplifting, action-packed, epic, educational, musical, crime, sci-fi, nostalgic, and children/family-friendly prompts.

## Data And Model Artifacts

The pushed repository keeps the files needed to understand and run the final product:

- final web app and backend code
- deployable catalog JSON
- notebooks that document and reproduce the project logic
- final review CSVs:
  - `data/bertopic_topic_review.csv`
  - `data/prompt_recommendation_evaluation.csv`
  - `data/prompt_recommendation_stress_summary.csv`

Large/generated/local files are ignored, including:

- `.venv/`
- `.env` and secret files
- local model folders
- raw export CSVs
- intermediate CSVs and NumPy embedding files

## Run Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
```

Start the backend and frontend together:

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

## API Endpoints

- `GET /health`
  Confirms that the backend is running and the catalog loaded.

- `GET /catalog/summary`
  Returns catalog size, year range, genres, content types, moods, and poster count.

- `POST /recommend`
  Accepts prompt/filter JSON and returns ranked recommendation results.

Example request:

```json
{
  "prompt": "I want something cute but not animation",
  "type": "all",
  "genre": "all",
  "mood": "all",
  "avoid": "none",
  "min_rating": 6.5,
  "min_votes": 30000,
  "year_from": 1990,
  "year_to": 2023,
  "limit": 20,
  "sort": "match"
}
```

## Deployment

The project is configured for:

- Netlify frontend: `https://mood-based-watch-recommender.netlify.app`
- Render backend: `https://mood-based-watch-recommender.onrender.com`

Netlify settings:

```text
Build command: leave empty
Publish directory: .
```

Render settings:

```text
Build command: pip install -r requirements-backend.txt
Start command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Health check path: /health
```

Render environment variable:

```text
ALLOWED_ORIGINS=https://mood-based-watch-recommender.netlify.app,https://mood-based-watch-recommender.onrender.com,http://localhost:8000,http://localhost:8765,http://127.0.0.1:8765
```

`config.js` is already set so the Netlify frontend calls the Render backend. Local development and Render same-origin serving still use the same host automatically.

## Security Notes

No API keys are required for the deployed recommender. Secret files are ignored through `.gitignore`, including `.env`, `.env.*`, key/certificate files, `.netlify/`, and `.render/`. Real API keys or service tokens should never be committed.
