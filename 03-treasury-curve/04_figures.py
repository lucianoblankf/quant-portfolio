"""04: zero / forward curve, curve snapshots and key-rate DV01."""

from pathlib import Path

import pandas as pd

from src import config, data, plots, reporting

reporting.section("04 Figures")

bonds = pd.read_parquet("data/processed/bonds.parquet")
quote_date = pd.Timestamp(config.QUOTE_DATE) if config.QUOTE_DATE else bonds["quote_date"].max()
cv, _, yields = data.curve_on(bonds, quote_date)
krd = pd.read_csv("tabs/key_rate_dv01.csv", index_col="pillar")
Path("figs").mkdir(exist_ok=True)

plots.plot_zero_forward(cv, yields, cv.valuation, quote_date).save(
    "figs/zero_forward_curve.png", width=8, height=4.5, dpi=300, verbose=False
)

snapshots = {}
for day in (*config.SNAPSHOT_DATES, str(quote_date.date())):
    stamp = pd.Timestamp(day)
    if (bonds["quote_date"] == stamp).any():
        snapshots[day] = data.curve_on(bonds, stamp)[0]
plots.plot_snapshots(snapshots).save("figs/curve_snapshots.png", width=8, height=4.5, dpi=300, verbose=False)

plots.plot_key_rate_dv01(krd, ["NTN-F 2033-01-01", "NTN-F 2037-01-01", "LTN 2029-01-01"]).save(
    "figs/key_rate_dv01.png", width=8, height=4.5, dpi=300, verbose=False
)
reporting.success("Figures saved to figs/")
