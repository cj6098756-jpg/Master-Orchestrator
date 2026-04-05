from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pipeline.schema import MACRO_DDL, RENKO_DDL, TICKS_DDL


@lru_cache(maxsize=1)
def get_engine() -> Engine | None:
    """Create and cache SQLAlchemy engine from env config."""
    url = os.getenv("TIMESCALEDB_URL")
    return create_engine(url) if url else None


def apply_schema() -> None:
    """Apply schema or print STUB warning when DB env is absent."""
    engine = get_engine()
    if engine is None:
        print("STUB: TIMESCALEDB_URL not configured; schema not applied")
        return

    with engine.begin() as conn:
        for ddl in (TICKS_DDL, RENKO_DDL, MACRO_DDL):
            for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
                conn.execute(text(stmt))
