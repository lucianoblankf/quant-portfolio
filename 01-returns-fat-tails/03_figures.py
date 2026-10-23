"""03: histogram and QQ plot for each asset."""

from pathlib import Path

import pandas as pd

from src import data, plots, reporting

reporting.section("03 Figures")

returns = pd.read_parquet("data/processed/returns.parquet")
labels = data.ASSET_LABELS.set_index("asset")["label"]
Path("figs").mkdir(exist_ok=True)

for asset, group in returns.groupby("asset"):
    r = group["log_return"].to_numpy()
    plots.plot_histogram(r, labels[asset]).save(
        f"figs/hist_{asset}.png", width=8, height=4.5, dpi=300, verbose=False
    )
    plots.plot_qq(r, labels[asset]).save(
        f"figs/qq_{asset}.png", width=5.5, height=5.5, dpi=300, verbose=False
    )
    reporting.success(f"Figures saved for {labels[asset]}")
