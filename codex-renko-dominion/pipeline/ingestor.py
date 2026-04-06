from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import text

from pipeline.db import get_engine
from pipeline.feeds import CSVTickReplay, FREDAdapter


class Ingestor:
    """Data ingestion utility for macro and tick sources."""

    def ingest_fred(self, series_ids: list[str], start: str, end: str, dry_run: bool = False) -> None:
        """Fetch and ingest FRED indicators."""
        adapter = FREDAdapter()
        total = 0
        engine = get_engine()
        for series_id in series_ids:
            rows = adapter.fetch(series_id, start, end)
            total += len(rows)
            if dry_run or engine is None:
                print(f"[DRY_RUN={dry_run}] Would insert {len(rows)} rows for {series_id}")
                continue
            with engine.begin() as conn:
                for row in rows:
                    conn.execute(
                        text(
                            "INSERT INTO macro_indicators (ts, series_id, value, source) VALUES (:ts, :series_id, :value, 'FRED')"
                        ),
                        {
                            "ts": datetime.fromisoformat(row["date"] + "T00:00:00"),
                            "series_id": series_id,
                            "value": float(row["value"]) if row["value"] != "." else 0.0,
                        },
                    )
        print(f"FRED ingest summary: series={len(series_ids)}, rows={total}, dry_run={dry_run}")

    def ingest_csv(self, path: str, symbol: str, dry_run: bool = False) -> None:
        """Read CSV ticks and ingest into Timescale."""
        replay = CSVTickReplay(path)
        df = replay.df
        engine = get_engine()
        if dry_run or engine is None:
            print(f"[DRY_RUN={dry_run}] Would insert {len(df)} ticks for {symbol}")
            return

        with engine.begin() as conn:
            for _, row in df.iterrows():
                conn.execute(
                    text("INSERT INTO ticks (ts, symbol, bid, ask) VALUES (:ts, :symbol, :bid, :ask)"),
                    {
                        "ts": pd.to_datetime(row["ts"]).to_pydatetime(),
                        "symbol": symbol,
                        "bid": float(row["bid"]),
                        "ask": float(row["ask"]),
                    },
                )
        print(f"CSV ingest summary: symbol={symbol}, rows={len(df)}, dry_run={dry_run}")
