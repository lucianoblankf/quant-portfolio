"""05: figures."""

from pathlib import Path

import pandas as pd

from src import config, data, plots, reporting
from src import engine as eng

reporting.section("05 Figures")

returns, yields, pf = data.load_processed()
Path("figs").mkdir(exist_ok=True)
size = {"dpi": 300, "verbose": False}

pnl = pd.read_parquet("data/processed/pnl_last_window.parquet")["pnl"]
cov_sample = returns[pf.factors].cov()
var_hist, es_hist = eng.historical(pf, returns, config.HIST_WINDOW, 0.99)
var_normal = eng.delta_normal(pf, cov_sample, 0.99)[0]
lines = {
    f"Historical VaR 99%: R$ {var_hist / 1e3:,.0f}k": var_hist,
    f"Expected shortfall 99%: R$ {es_hist / 1e3:,.0f}k": es_hist,
    f"Delta-normal VaR 99%: R$ {var_normal / 1e3:,.0f}k": var_normal,
}
plots.plot_pnl_distribution(pnl, lines).save("figs/pnl_distribution.png", width=8, height=4.5, **size)

components = pd.read_csv("tabs/component_var.csv", index_col="factor")
plots.plot_component_var(components).save("figs/component_var.png", width=7.5, height=4, **size)

backtest = pd.read_parquet("data/processed/backtest_series.parquet")
plots.plot_backtest(backtest).save("figs/backtest.png", width=10, height=4.5, **size)

plots.plot_stress(pd.read_csv("tabs/stress.csv")).save("figs/stress.png", width=9, height=4, **size)
reporting.success("Figures saved to figs/")
