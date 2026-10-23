"""Data helpers: download and read the raw price file."""

from pathlib import Path

import janitor  # noqa: F401  (registers DataFrame.clean_names)
import pandas as pd

RAW_FILE = Path("data/raw/prices.csv")
START = "2010-01-01"
ASSET_LABELS = pd.DataFrame(
    {"asset": ["ibovespa", "usd_brl"], "label": ["Ibovespa", "USD/BRL"], "ticker": ["^BVSP", "BRL=X"]}
)


def download_raw_prices(path: Path = RAW_FILE, start: str = START) -> Path:
    """Download daily closing prices from Yahoo Finance and save them as the raw file.

    The raw file is only written when it does not exist yet.
    """
    if path.exists():
        return path

    import yfinance as yf

    raw = yf.download(ASSET_LABELS["ticker"].tolist(), start=start, auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError("Download returned no data. Check your connection and try again.")
    prices = (
        raw["Close"]
        .rename(columns=dict(zip(ASSET_LABELS["ticker"], ASSET_LABELS["label"])))
        .loc[:, ASSET_LABELS["label"].tolist()]
        .rename_axis("date")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path)
    return path


def read_raw_prices(path: Path = RAW_FILE) -> pd.DataFrame:
    """Read the raw prices with sanitised column names (date, ibovespa, usd_brl)."""
    return pd.read_csv(path, parse_dates=["date"]).clean_names()
