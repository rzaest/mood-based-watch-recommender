# Mood-Based Watch Recommender

A deployable mood-aware movie and TV recommendation project. The product lets a user describe what they want to watch in natural language, optionally add filters, and receive ranked movie/show recommendations with poster-style cover images, ratings, genres, emotional facets, and explanation text.

## Live App Entry Point

Open `index.html` after deployment. The app is fully static and works on Netlify without a server process.

The deployed product is connected to the final recommender output through `assets/data/catalog.json`. On page load, `app.js` fetches that catalog, parses the user's prompt in the browser, scores the catalog, applies the selected filters, and renders the ranked recommendations. This is the Netlify-compatible version of the backend logic: the Python notebooks build the final model/features, and the web app consumes the exported static catalog.

Important files for the web product:

- `index.html` - main web app page.
- `styles.css` - responsive UI styling.
- `app.js` - browser-side recommendation logic, prompt parsing, filters, scoring, poster display, and rendering.
- `assets/data/catalog.json` - compact deployable catalog generated from the final NLP feature table.
- `netlify.toml` - Netlify static-site configuration.

## Product Features

The app supports:

- Natural-language prompts such as `I feel sad and heartbroken and I want to watch something joyous and comedic`.
- Format selectors for all formats, movies, TV, and shorts.
- Automatic format detection from prompts. If the prompt explicitly asks for a movie or film, only movies are displayed. If the prompt asks for a show, TV, or series, TV formats are displayed.
- Genre, mood, avoid-signal, rating, vote, year, result-count, and sorting controls.
- Explicit avoid handling for prompts such as `not scary`, `not sad`, `no crime`, `no heavy drama`, or `please do not destroy me`.
- A minimal interface with the main prompt and format controls visible first, plus optional advanced filters inside the `Refine results` panel.
- A connected-catalog status line showing that the web app has loaded the deployable recommendation data.
- High-quality poster/cover display. The catalog includes poster URLs for all 7,848 titles, using IMDb-hosted suggestion artwork where available and an IMDb-ID poster fallback for the remaining titles.

## Model And Notebook Files

The main modeling notebook is:

- `01_bertopic_nlp_pipeline.ipynb`

It contains the final NLP pipeline, including:

- sentence-embedding based semantic features;
- BERTopic/KMeans topic assignment;
- human-readable topic review labels;
- low-confidence topic flags;
- weighted emotional and narrative facets;
- prompt intent parsing;
- stress tests for difficult prompts.

Useful final review files:

- `data/bertopic_topic_review.csv` - topic labels, quality flags, dominant genres, and sample titles.
- `data/prompt_recommendation_stress_summary.csv` - hard-prompt stress-test summary with score bands and warnings.
- `data/prompt_recommendation_evaluation.csv` - detailed recommendation rows for the stress-test prompts.

Presentation files:

- `presentation.qmd` - Quarto presentation source.
- `presentation.html` - rendered presentation.
- `presentation.css` - presentation styling.
- `output/pdf/mood_based_watch_recommender_presentation.pdf` - exported presentation PDF.

## Data Source And Cleaning

The project began with an IMDb movies/shows dataset and then rebuilt or improved descriptions using verified sources. The final app does not depend on the original raw CSV at runtime. It uses `assets/data/catalog.json`, which was generated from the final model feature table.

## Stress Test Summary

The final stress test covers difficult prompts with:

- typos;
- imperfect English;
- contradictions;
- current emotion vs desired content;
- explicit content exclusions;
- vague emotional language;
- movie/TV format intent.

The latest run produced mostly strong and usable results, with one borderline prompt involving an inspiring documentary that should avoid both war and bleakness. That limitation is kept visible in the stress summary because it is a realistic ambiguity in the catalog rather than a hidden failure.

## Netlify Deployment

This repository is ready for Netlify as a static site.

Recommended Netlify settings:

- Build command: leave empty.
- Publish directory: `.`

After pushing to GitHub, connect the repository in Netlify and deploy from the default branch.

## What Is Not Included

The old `rule_based_recommender.ipynb` and `content_based_recommender.ipynb` notebooks are intentionally not part of the final deliverable because the NLP prompt-aware recommender replaced them.

The local Python virtual environment and trained model directory are also excluded from GitHub because the deployed app is static and uses the compact catalog JSON instead.
