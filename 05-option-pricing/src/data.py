"""Option-chain data helpers: download the raw SPY chain once and read it."""

from pathlib import Path

import janitor  # noqa: F401  (registers DataFrame.clean_names)
import numpy as np
import pandas as pd

from src import config

RAW_FILE = Path("data/raw/spy_chain.csv")


def download_raw_chain(path: Path = RAW_FILE) -> Path:
    """Download the option chain with expiry closest to `config.SMILE_DAYS` days, plus the
    13-week T-bill rate. Never overwrites an existing raw file."""
    if path.exists():
        return path

    import yfinance as yf

    ticker = yf.Ticker(config.SMILE_TICKER)
    spot = float(ticker.history(period="5d")["Close"].iloc[-1])
    today = pd.Timestamp.today().normalize()
    expiries = pd.to_datetime(ticker.options)
    expiry = expiries[np.argmin(np.abs((expiries - today).days - config.SMILE_DAYS))]
    chain = ticker.option_chain(expiry.strftime("%Y-%m-%d"))
    rf = float(yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1]) / 100

    frames = []
    for kind, quotes in (("call", chain.calls), ("put", chain.puts)):
        frames.append(
            quotes[["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]].assign(kind=kind)
        )
    out = pd.concat(frames).assign(spot=spot, expiry=expiry.date(), asof=today.date(), rf=rf)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return path


def read_raw_chain(path: Path = RAW_FILE) -> pd.DataFrame:
    """Read the raw chain with clean names (strike, bid, ask, ..., implied_volatility, kind, ...)."""
    return pd.read_csv(path, parse_dates=["expiry", "asof"]).clean_names(case_type="snake")
