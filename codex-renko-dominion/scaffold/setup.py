from __future__ import annotations

from pathlib import Path

PACKAGE_DIRS = ["sessions", "data", "logs", "mwp"]


def run_setup() -> bool:
    """Packaging/bootstrap convenience only (no runtime orchestration)."""
    for folder in PACKAGE_DIRS:
        Path(folder).mkdir(parents=True, exist_ok=True)
    return True
