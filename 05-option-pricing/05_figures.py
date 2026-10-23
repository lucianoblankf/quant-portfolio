"""05: figures."""

from pathlib import Path

import pandas as pd

from src import plots, reporting

reporting.section("05 Figures")

Path("figs").mkdir(exist_ok=True)
size = {"dpi": 300, "verbose": False}

plots.plot_mc_error(pd.read_csv("tabs/monte_carlo.csv")).save("figs/mc_error.png", width=6, height=4.2, **size)
plots.plot_tree_convergence(pd.read_csv("tabs/binomial.csv")).save(
    "figs/tree_convergence.png", width=6, height=4.2, **size
)
plots.plot_hedging_error(pd.read_parquet("data/processed/hedging_pnl.parquet")).save(
    "figs/hedging_error.png", width=6, height=4.2, **size
)
plots.plot_wrong_vol(pd.read_csv("tabs/hedging_vol_error.csv")).save(
    "figs/hedging_wrong_vol.png", width=6, height=4.2, **size
)
plots.plot_greeks().save("figs/greeks.png", width=10, height=6.5, **size)

if Path("tabs/spy_smile.csv").exists():
    smile = pd.read_csv("tabs/spy_smile.csv")
    summary = pd.read_csv("tabs/smile_summary.csv")
    plots.plot_smile(smile, summary["atm_iv"].iloc[0], summary["days"].iloc[0]).save(
        "figs/spy_smile.png", width=7.5, height=4.5, **size
    )
reporting.success("Figures saved to figs/")
