"""Loads shop-level rate config from ``quote_params.json`` (with safe defaults).

This mirrors the role of ``quote-params.json`` in the in-house
``tlk-quoting-engine`` so GVPP's numbers use the same cost basis.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULTS: dict = {
    "machine_hourly_rate_usd": 95.00,
    "setup_time_minutes": {"swiss": 20, "lathe": 15, "mill": 30},
    "tooling_amortization_per_cycle_usd": 0.08,
    "overhead_multiplier": 1.25,
    "margin_percent": 35,
    "stock_waste_factor": 0.15,
    "cycle_time_estimation": {
        "base_mrr_in3_per_min": 1.0,
        "lathe_mrr_multiplier": 1.3,
        "finish_seconds_per_in2": 1.5,
        "handling_seconds": 30,
    },
    "operations": {
        "max_rpm": 10000,
        "index_seconds": 2.0,
        "drill_feed_factor": 0.6,
        "groove_feed_factor": 0.5,
        "cutoff_feed_factor": 0.5,
        "peck_penalty": 0.4,
        "thread_retract_seconds": 1.0,
    },
    "lead_time": {
        "base_days": 5,
        "days_per_25_units": 1,
        "hard_material_penalty_days": 3,
        "low_confidence_penalty_days": 2,
    },
}

_BACKEND_DIR = Path(__file__).resolve().parent.parent
# Committed example rates, then an optional gitignored local override. Keep your
# real shop rates in quote_params.local.json so they never hit a public repo.
_PARAMS_PATHS = (
    _BACKEND_DIR / "quote_params.json",
    _BACKEND_DIR / "quote_params.local.json",
)


def _overlay(params: dict, overrides: dict) -> None:
    for key, value in overrides.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(params.get(key), dict):
            params[key].update(value)
        else:
            params[key] = value


def load_params() -> dict:
    """Return shop params: defaults, then quote_params.json, then a local override."""
    params = json.loads(json.dumps(DEFAULTS))  # deep copy
    for path in _PARAMS_PATHS:
        if not path.exists():
            continue
        try:
            _overlay(params, json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            continue
    return params


PARAMS: dict = load_params()
