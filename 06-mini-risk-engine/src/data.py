"""Data helpers: raw prices (Yahoo Finance), raw Tesouro Direto file, factor returns, portfolio."""

import urllib.request
from pathlib import Path

import janitor  # noqa: F401  (registers DataFrame.clean_names)
import numpy as np
import pandas as pd

from src import config
from src.engine import Portfolio

RAW_PRICES = Path("data/raw/prices.csv")
RAW_TESOURO = Path("data/raw/tesouro_direto.csv")
TESOURO_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
    "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)


def download_raw_prices(path: Path = RAW_PRICES) -> Path:
    """Download daily closes of the stocks and USD/BRL once. Never overwrites an existing file."""
    if not path.exists():
        import yfinance as yf

        raw = yf.download(list(config.TICKERS), start=config.PRICE_START, auto_adjust=True, progress=False)["Close"]
        path.parent.mkdir(parents=True, exist_ok=True)
        raw.rename(columns=config.TICKERS).rename_axis("date").to_csv(path)
    return path


def download_raw_tesouro(path: Path = RAW_TESOURO) -> Path:
    """Download the Tesouro Transparente file once. Never overwrites an existing file."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(TESOURO_URL, path)
    return path


def read_prices(path: Path = RAW_PRICES) -> pd.DataFrame:
    """Raw prices with clean names (date, petr4, vale3, ..., usdbrl)."""
    return pd.read_csv(path).clean_names().assign(date=lambda d: pd.to_datetime(d["date"]))


def zero_yield(path: Path = RAW_TESOURO, tenor: float = config.BOND_TENOR_YEARS) -> pd.Series:
    """Daily zero rate at `tenor` years: linear interpolation of the LTN yields around it."""
    ltn = (
        pd.read_csv(path, sep=";", decimal=",")
        .clean_names()
        .loc[lambda d: d["tipo_titulo"] == "Tesouro Prefixado"]
        .assign(
            quote_date=lambda d: pd.to_datetime(d["data_base"], format="%d/%m/%Y"),
            ttm=lambda d: (pd.to_datetime(d["data_vencimento"], format="%d/%m/%Y") - pd.to_datetime(d["data_base"], format="%d/%m/%Y")).dt.days / 365.25,
            yield_buy=lambda d: d["taxa_compra_manha"] / 100,
        )
    )
    out = {}
    for day, group in ltn.groupby("quote_date"):
        group = group.sort_values("ttm")
        if group["ttm"].min() <= tenor <= group["ttm"].max() and len(group) >= 2:
            out[day] = np.interp(tenor, group["ttm"], group["yield_buy"])
    return pd.Series(out).sort_index().rename("zero_yield").rename_axis("date")


def build_factor_returns(prices: pd.DataFrame, yields: pd.Series) -> pd.DataFrame:
    """Daily factor moves: log returns of stocks and FX, change of the 3-year zero yield (decimal).

    Yield changes are kept only between consecutive trading days (at most 4 calendar days apart).
    """
    log_returns = np.log(prices.set_index("date")[list(config.TICKERS.values())].dropna()).diff().dropna()
    gap = pd.Series(yields.index, index=yields.index).diff().dt.days
    rate = yields.diff().loc[gap <= 4].rename("rate")
    return log_returns.join(rate, how="inner").dropna()


def build_portfolio(today_yield: float) -> Portfolio:
    """The portfolio of `config`, with the bond priced at today's 3-year zero yield."""
    return Portfolio(
        equity=dict(config.EQUITY),
        fx=dict(config.FX),
        bond_value=config.BOND_VALUE,
        bond_years=config.BOND_TENOR_YEARS,
        bond_yield=float(today_yield),
        rate_factor="rate",
    )


def load_processed():
    """Factor returns, zero-yield series and the portfolio, from data/processed/."""
    returns = pd.read_parquet("data/processed/factor_returns.parquet")
    yields = pd.read_parquet("data/processed/zero_yield.parquet")["zero_yield"]
    return returns, yields, build_portfolio(yields.iloc[-1])
