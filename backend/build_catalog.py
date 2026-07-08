"""Build the deployable catalog JSON from the final NLP feature table.

The notebooks create `data/final_nlp_recommender_features.csv`. This script
turns that table into the runtime artifact consumed by the FastAPI backend:
`assets/data/catalog.json`.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "final_nlp_recommender_features.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "assets" / "data" / "catalog.json"

FACET_COLUMNS = {
    "mood": "top_mood_facets",
    "tone": "top_tone_facets",
    "themes": "top_themes_facets",
    "conflict_type": "top_conflict_type_facets",
    "pace": "top_pace_facets",
    "arc": "top_emotional_arc_facets",
    "setting": "top_setting_facets",
}

REQUIRED_COLUMNS = {
    "tconst",
    "content_type",
    "primary_title",
    "display_title",
    "original_title",
    "release_year",
    "genres",
    "average_rating",
    "num_votes",
    "weighted_rating",
    "description",
    "bertopic_topic_label",
    "bertopic_topic_quality",
    "bertopic_low_confidence",
}


def split_genres(value: Any) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return ["Unknown"]
    return [part.strip() for part in str(value).split(",") if part.strip()] or ["Unknown"]


def safe_number(value: Any, default: float = 0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    return int(round(safe_number(value, default)))


def parse_facets(value: Any) -> list[dict[str, float]]:
    if pd.isna(value) or not str(value).strip():
        return []
    text = str(value).strip()

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            facets = []
            for entry in parsed:
                if isinstance(entry, dict) and "label" in entry:
                    facets.append({"label": str(entry["label"]), "score": float(entry.get("score", 0.1))})
                elif isinstance(entry, (list, tuple)) and entry:
                    facets.append({"label": str(entry[0]), "score": float(entry[1]) if len(entry) > 1 else 0.1})
                elif isinstance(entry, str):
                    facets.append({"label": entry, "score": 0.1})
            return facets[:5]
    except (ValueError, SyntaxError, TypeError):
        pass

    facets = []
    for raw in re.split(r"\s*[|;,]\s*", text):
        if not raw:
            continue
        match = re.match(r"(.+?)[=:]\s*([0-9.]+)$", raw)
        if match:
            facets.append({"label": match.group(1).strip(), "score": float(match.group(2))})
        else:
            facets.append({"label": raw.strip(), "score": 0.1})
    return facets[:5]


def build_catalog(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Final feature table not found: {input_path}")

    df = pd.read_csv(input_path)
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Final feature table is missing required columns: {', '.join(missing)}")

    items = []
    for _, row in df.iterrows():
        genres = split_genres(row["genres"])
        facets = {key: parse_facets(row.get(column)) for key, column in FACET_COLUMNS.items()}
        title_id = str(row["tconst"])
        title = str(row.get("primary_title") or row.get("display_title") or row.get("original_title") or title_id)
        description = str(row.get("description") or "")
        search_text = " ".join(
            [
                title,
                str(row.get("display_title") or ""),
                str(row.get("original_title") or ""),
                " ".join(genres),
                description,
                str(row.get("bertopic_topic_label") or ""),
                " ".join(facet["label"] for group in facets.values() for facet in group),
            ]
        ).lower()

        items.append(
            {
                "id": title_id,
                "type": str(row["content_type"]),
                "title": title,
                "displayTitle": str(row.get("display_title") or title),
                "originalTitle": str(row.get("original_title") or title),
                "year": safe_int(row.get("release_year")),
                "genres": genres,
                "rating": round(safe_number(row.get("average_rating")), 3),
                "votes": safe_int(row.get("num_votes")),
                "weightedRating": round(safe_number(row.get("weighted_rating")), 3),
                "topic": str(row.get("bertopic_topic_label") or ""),
                "topicQuality": str(row.get("bertopic_topic_quality") or ""),
                "lowConfidence": bool(row.get("bertopic_low_confidence")),
                "description": description,
                "facets": facets,
                "searchText": search_text,
                "posterUrl": f"https://images.metahub.space/poster/medium/{title_id}/img",
                "posterSource": "Metahub IMDb-id poster fallback",
            }
        )

    years = [item["year"] for item in items if item["year"]]
    meta = {
        "generatedFrom": str(input_path.relative_to(PROJECT_ROOT)),
        "count": len(items),
        "genres": sorted({genre for item in items for genre in item["genres"]}),
        "types": sorted({item["type"] for item in items}),
        "yearMin": min(years) if years else None,
        "yearMax": max(years) if years else None,
        "posterSource": "Metahub IMDb-id poster fallback",
        "posterCount": len(items),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"meta": meta, "items": items}, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {len(items):,} titles to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_catalog(args.input, args.output)


if __name__ == "__main__":
    main()
