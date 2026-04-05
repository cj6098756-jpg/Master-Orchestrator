from __future__ import annotations

import os

import pandas as pd
import requests


class FREDAdapter:
    """Adapter for FRED observations API."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def fetch(self, series_id: str, start: str, end: str) -> list[dict]:
        """Fetch FRED observations for a date range."""
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("WARNING: FRED_API_KEY not configured; returning empty list")
            return []

        params = {
            "series_id": series_id,
            "observation_start": start,
            "observation_end": end,
            "api_key": api_key,
            "file_type": "json",
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("observations", [])


class CSVTickReplay:
    """Simple CSV tick replayer producing mid-price series."""

    def __init__(self, path: str) -> None:
        self.df = pd.read_csv(path)
        required = {"ts", "symbol", "bid", "ask"}
        if not required.issubset(set(self.df.columns)):
            raise ValueError(f"CSV missing columns: {required}")

    def prices(self) -> list[float]:
        """Return mid prices computed from bid/ask columns."""
        mids = (self.df["bid"].astype(float) + self.df["ask"].astype(float)) / 2.0
        return mids.tolist()
