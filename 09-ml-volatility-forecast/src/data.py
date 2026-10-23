"""Data helpers: download the raw OHLC file once and read it."""

from pathlib import Path

import janitor  # noqa: F401  (registers DataFrame.clean_names)
import pandas as pd

from src import config

RAW_FILE = Path("data/raw/ohlc.csv")


def download_raw_ohlc(path: Path = RAW_FILE) -> Path:
    """Download Ibovespa OHLC and the USD/BRL close once. Never overwrites an existing file."""
    if path.exists():
        return path

    import yfinance as yf

    ibov = yf.download(config.TICKER, start=config.DATA_START, auto_adjust=True, progress=False)
    ibov.columns = ibov.columns.get_level_values(0)
    fx = yf.download(config.FX_TICKER, start=config.DATA_START, auto_adjust=True, progress=False)
    fx.columns = fx.columns.get_level_values(0)
    out = ibov[["Open", "High", "Low", "Close"]].join(fx["Close"].rename("fx"), how="left").rename_axis("date")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path)
    return path


def read_ohlc(path: Path = RAW_FILE):
    """Ibovespa OHLC (rows with zero range dropped) and the forward-filled USD/BRL close."""
    raw = pd.read_csv(path).clean_names().assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")
    raw = raw.loc[(raw["high"] > raw["low"]) & (raw["low"] > 0)]
    return raw[["open", "high", "low", "close"]], raw["fx"].ffill()
