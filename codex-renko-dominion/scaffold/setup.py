from __future__ import annotations

import os
from pathlib import Path

REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "TIMESCALEDB_URL", "FRED_API_KEY", "MT4_ZMQ_HOST"]


def run_setup() -> bool:
    set_count = 0
    for key in REQUIRED_KEYS:
        ok = bool(os.getenv(key))
        set_count += 1 if ok else 0
        print(f"{'✓' if ok else '✗'} {key}")

    for folder in ["sessions", "data", "logs", "mwp"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
    print(f"Summary: {set_count}/{len(REQUIRED_KEYS)} required vars set")

    offline_ready = sum(1 for k in ["TIMESCALEDB_URL", "FRED_API_KEY", "MT4_ZMQ_HOST"] if os.getenv(k)) >= 2
    return bool(os.getenv("ANTHROPIC_API_KEY")) or offline_ready
