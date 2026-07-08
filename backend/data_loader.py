import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = PROJECT_ROOT / "assets" / "data" / "catalog.json"

REQUIRED_META_KEYS = {"count", "genres", "types", "yearMin", "yearMax"}
REQUIRED_ITEM_KEYS = {
    "id",
    "type",
    "title",
    "year",
    "genres",
    "rating",
    "votes",
    "weightedRating",
    "description",
    "facets",
    "searchText",
}


class CatalogLoadError(RuntimeError):
    """Raised when the deployable catalog is missing or malformed."""


def load_catalog(path: Path | str = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise CatalogLoadError(f"Catalog file is missing: {catalog_path}")

    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(f"Catalog file is not valid JSON: {exc}") from exc

    meta = catalog.get("meta")
    items = catalog.get("items")
    if not isinstance(meta, dict) or not isinstance(items, list):
        raise CatalogLoadError("Catalog must contain a 'meta' object and an 'items' list.")

    missing_meta = sorted(REQUIRED_META_KEYS - set(meta))
    if missing_meta:
        raise CatalogLoadError(f"Catalog meta is missing required keys: {', '.join(missing_meta)}")

    if not items:
        raise CatalogLoadError("Catalog contains no title items.")

    missing_item_keys = sorted(REQUIRED_ITEM_KEYS - set(items[0]))
    if missing_item_keys:
        raise CatalogLoadError(f"Catalog items are missing required keys: {', '.join(missing_item_keys)}")

    return catalog
