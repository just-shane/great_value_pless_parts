"""Live speeds & feeds from the Datum Supabase ``cutting_presets`` table.

Operations mode pulls surface speed (SFM) and feed-per-rev per material from the
in-house database at runtime. Credentials live in a gitignored local config
(``backend/supabase.local.json``) or environment variables — never in the repo.

Config (either form):
    backend/supabase.local.json:  {"url": "https://<ref>.supabase.co", "service_key": "<key>"}
    env:                          DATUM_SUPABASE_URL, DATUM_SUPABASE_KEY

The query mirrors what was validated against the live DB: median ``v_c`` (SFM)
and median ``v_f / n`` (feed per rev) over the presets for a material category.
Returns ``None`` when no config is present or the DB is unreachable; the caller
then flags the quote rather than silently inventing numbers.
"""

from __future__ import annotations

import json
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "supabase.local.json"

# GVPP material key -> Fusion CAM material_query category present in cutting_presets.
MATERIAL_CATEGORY_MAP: dict[str, str] = {
    "aluminum_6061": "Aluminum",
    "aluminum_7075": "Aluminum",
    "steel_1018": "Low Carbon Steel",
    "stainless_304": "Stainless Steel",
    "stainless_316": "Stainless Steel",
    "brass_360": "Brass",
    "titanium_ti6al4v": "Titanium",
    "peek": "Plastics",
    "abs": "Plastics",
    "delrin": "Plastics",
}
_DEFAULT_CATEGORY = "Low Carbon Steel"


@dataclass(frozen=True)
class SpeedsFeeds:
    material_category: str
    sfm: float
    feed_per_rev: float
    sample_size: int
    source: str  # "datum_supabase"


_cache: dict[str, SpeedsFeeds | None] = {}


def _load_config() -> tuple[str, str] | None:
    url = os.environ.get("DATUM_SUPABASE_URL")
    key = os.environ.get("DATUM_SUPABASE_KEY")
    if url and key:
        return url.rstrip("/"), key
    if _CONFIG_PATH.exists():
        try:
            cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        url = cfg.get("url")
        key = cfg.get("service_key") or cfg.get("key")
        if url and key:
            return url.rstrip("/"), key
    return None


def _fetch_rows(url: str, key: str, category: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {"select": "v_c,v_f,n", "material_query": f"eq.{category}", "v_c": "gt.0"},
        safe="=.",
    )
    endpoint = f"{url}/rest/v1/cutting_presets?{query}"
    req = urllib.request.Request(
        endpoint,
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def lookup(material_key: str) -> SpeedsFeeds | None:
    """Return live speeds & feeds for a material, or ``None`` if unavailable."""
    category = MATERIAL_CATEGORY_MAP.get(material_key, _DEFAULT_CATEGORY)
    if category in _cache:
        return _cache[category]

    config = _load_config()
    if not config:
        _cache[category] = None
        return None

    url, key = config
    try:
        rows = _fetch_rows(url, key, category)
    except (urllib.error.URLError, ValueError, TimeoutError):
        return None  # transient — don't poison the cache

    sfms = [r["v_c"] for r in rows if r.get("v_c")]
    feeds = [r["v_f"] / r["n"] for r in rows if r.get("v_f") and r.get("n")]
    if not sfms or not feeds:
        _cache[category] = None
        return None

    result = SpeedsFeeds(
        material_category=category,
        sfm=round(statistics.median(sfms), 1),
        feed_per_rev=round(statistics.median(feeds), 5),
        sample_size=len(rows),
        source="datum_supabase",
    )
    _cache[category] = result
    return result
