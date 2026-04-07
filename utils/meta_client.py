"""
Meta data client for the Streamlit dashboard.

Architecture:
  - Primary source: JSON cache files in meta_cache/ folder
  - Cache is refreshed by Claude (via MCP) on demand or on a schedule
  - No direct API calls from Streamlit needed — no token management

Cache files:
  meta_cache/campaigns_last_7d.json
  meta_cache/campaigns_last_14d.json
  meta_cache/campaigns_last_30d.json
  meta_cache/campaigns_this_month.json
  meta_cache/campaigns_last_month.json
  meta_cache/campaigns_yesterday.json

To refresh data: ask Claude "refresh Meta Live data" and it will
re-pull from all 9 accounts via MCP and update the cache files.
"""

from __future__ import annotations
import json
import os
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meta_cache")


def _cache_path(date_preset: str) -> str:
    # Sanitize for filename — replace slashes/spaces with underscores
    safe = date_preset.replace("/", "-").replace(" ", "_")
    return os.path.join(CACHE_DIR, f"campaigns_{safe}.json")


def load_from_cache(date_preset: str = "last_7d") -> tuple[list[dict], str | None]:
    """
    Load campaign data from local cache file.
    Returns (rows, fetched_at_str) or ([], None) if not found.
    """
    path = _cache_path(date_preset)
    if not os.path.exists(path):
        return [], None
    try:
        with open(path) as f:
            data = json.load(f)
        rows = data.get("campaigns", [])
        fetched_at = data.get("fetched_at")
        return rows, fetched_at
    except Exception:
        return [], None


def cache_age_minutes(date_preset: str = "last_7d") -> float | None:
    """Return how many minutes ago the cache was last updated, or None."""
    path = _cache_path(date_preset)
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        age = (datetime.now().timestamp() - mtime) / 60
        return round(age, 1)
    except Exception:
        return None


def _province_breakdown_path(date_preset: str) -> str:
    safe = date_preset.replace("/", "-").replace(" ", "_")
    return os.path.join(CACHE_DIR, f"province_breakdown_{safe}.json")


def load_province_breakdown(date_preset: str = "last_7d") -> dict[str, dict]:
    """
    Load province-level breakdown for national campaigns.
    Returns dict keyed by campaign_id → {campaign_name, rows: [{region, spend, impressions, leads, cpm}]}
    Returns {} if no cache found.
    """
    path = _province_breakdown_path(date_preset)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("breakdowns", {})
    except Exception:
        return {}
