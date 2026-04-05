from __future__ import annotations

TICKS_DDL = """
CREATE TABLE IF NOT EXISTS ticks (
    ts          TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    bid         DOUBLE PRECISION NOT NULL,
    ask         DOUBLE PRECISION NOT NULL,
    mid         DOUBLE PRECISION GENERATED ALWAYS AS ((bid+ask)/2) STORED
);
SELECT create_hypertable('ticks','ts',if_not_exists=>TRUE);
CREATE INDEX IF NOT EXISTS ix_ticks_symbol ON ticks(symbol, ts DESC);
""".strip()

RENKO_DDL = """
CREATE TABLE IF NOT EXISTS renko_bricks (
    ts          TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    tier        TEXT NOT NULL,
    direction   TEXT NOT NULL,
    open_price  DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    brick_size  DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('renko_bricks','ts',if_not_exists=>TRUE);
""".strip()

MACRO_DDL = """
CREATE TABLE IF NOT EXISTS macro_indicators (
    ts          TIMESTAMPTZ NOT NULL,
    series_id   TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    source      TEXT NOT NULL DEFAULT 'FRED'
);
SELECT create_hypertable('macro_indicators','ts',if_not_exists=>TRUE);
""".strip()
