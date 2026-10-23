"""Tesouro Direto data helpers: download the raw file, read it, build the market on a date."""

import urllib.request
from pathlib import Path

import janitor  # noqa: F401  (registers DataFrame.clean_names)
import pandas as pd

from src import curve as c

RAW_FILE = Path("data/raw/tesouro_direto.csv")
URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
    "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)
KIND = {"Tesouro Prefixado": "LTN", "Tesouro Prefixado com Juros Semestrais": "NTN-F"}


def download_raw_tesouro(path: Path = RAW_FILE) -> Path:
    """Download the raw Tesouro Transparente file once. Never overwrites an existing file."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, path)
    return path


def read_bonds(path: Path = RAW_FILE) -> pd.DataFrame:
    """LTN and NTN-F quotes with clean names: kind, quote_date, maturity, yield_buy, pu_buy."""
    return (
        pd.read_csv(path, sep=";", decimal=",")
        .clean_names()
        .loc[lambda d: d["tipo_titulo"].isin(KIND)]
        .assign(
            kind=lambda d: d["tipo_titulo"].map(KIND),
            quote_date=lambda d: pd.to_datetime(d["data_base"], format="%d/%m/%Y"),
            maturity=lambda d: pd.to_datetime(d["data_vencimento"], format="%d/%m/%Y"),
            yield_buy=lambda d: d["taxa_compra_manha"] / 100,
            pu_buy=lambda d: d["pu_compra_manha"],
        )
        .loc[:, ["kind", "quote_date", "maturity", "yield_buy", "pu_buy"]]
        .reset_index(drop=True)
    )


def market_on(bonds: pd.DataFrame, quote_date: pd.Timestamp):
    """Instruments quoted on `quote_date`, the valuation date (next business day) and yields.

    Since 2024 the published PUs reconcile to the quoted yields only when discounted from
    the next business day, so that is the valuation date.
    """
    day = bonds.loc[bonds["quote_date"] == quote_date]
    valuation = c.next_business_day(quote_date.date())
    instruments = [(r.kind, r.maturity.date(), float(r.pu_buy)) for r in day.itertuples()]
    yields = {(r.kind, r.maturity.date()): r.yield_buy for r in day.itertuples()}
    return valuation, instruments, yields


def curve_on(bonds: pd.DataFrame, quote_date: pd.Timestamp):
    """Bootstrapped curve for a quote date: (curve, instruments, yields)."""
    valuation, instruments, yields = market_on(bonds, quote_date)
    return c.bootstrap(valuation, instruments), instruments, yields
