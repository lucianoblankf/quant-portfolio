"""04: implied volatilities of SPY options with our own solver, and the smile."""

from pathlib import Path

import pandas as pd

from src import config, data, reporting
from src import options as o

reporting.section("04 Volatility smile")

if not Path("data/raw/spy_chain.csv").exists():
    reporting.warn("No raw chain, smile skipped")
else:
    chain = data.read_raw_chain()
    spot, rf = chain["spot"].iloc[0], chain["rf"].iloc[0]
    years = max((chain["expiry"].iloc[0] - chain["asof"].iloc[0]).days, 1) / 365
    q = config.SMILE_DIVIDEND_YIELD

    # Out-of-the-money quotes only: more liquid and less affected by early exercise
    smile = (
        chain.loc[(chain["bid"] > 0) & (chain["ask"] > 0)]
        .assign(mid=lambda d: (d["bid"] + d["ask"]) / 2)
        .loc[lambda d: ((d["kind"] == "call") & (d["strike"] >= spot)) | ((d["kind"] == "put") & (d["strike"] < spot))]
        .loc[lambda d: (d["strike"] > 0.85 * spot) & (d["strike"] < 1.15 * spot)]
        .assign(
            iv=lambda d: [
                o.implied_vol(m, spot, k, years, rf, kind, q) for m, k, kind in zip(d["mid"], d["strike"], d["kind"])
            ]
        )
        .dropna(subset=["iv"])
        .sort_values("strike")
        .reset_index(drop=True)
    )
    smile.to_csv("tabs/spy_smile.csv", index=False)

    atm = smile.iloc[(smile["strike"] - spot).abs().argmin()]["iv"]
    yahoo = smile["implied_volatility"].to_numpy()
    valid = yahoo > 0.01
    gap = float(pd.Series(abs(smile["iv"].to_numpy()[valid] - yahoo[valid])).median())
    summary = pd.DataFrame(
        {
            "spot": [spot],
            "days": [years * 365],
            "rf": [rf],
            "quotes": [len(smile)],
            "atm_iv": [atm],
            "iv_below_95": [smile.loc[smile["strike"] < 0.95 * spot, "iv"].mean()],
            "iv_above_105": [smile.loc[smile["strike"] > 1.05 * spot, "iv"].mean()],
            "median_gap_to_yahoo": [gap],
        }
    )
    reporting.save_table(summary, "smile_summary")
    reporting.show_table(summary, f"{config.SMILE_TICKER} smile summary")
