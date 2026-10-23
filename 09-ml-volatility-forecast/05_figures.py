"""05: figures."""

from pathlib import Path

import pandas as pd

from src import config, plots, reporting

reporting.section("05 Figures")

Path("figs").mkdir(exist_ok=True)
size = {"dpi": 300, "verbose": False}

forecasts = pd.read_parquet("data/processed/forecasts.parquet")
plots.plot_forecast_window(forecasts, "2019-10-01", "2021-03-31").save("figs/forecast_covid.png", width=10, height=4.5, **size)
plots.plot_qlike(pd.read_csv("tabs/accuracy_full.csv")).save("figs/qlike_by_model.png", width=7, height=4, **size)
plots.plot_importance(pd.read_csv("tabs/feature_importance.csv")).save("figs/feature_importance.png", width=7, height=4, **size)
plots.plot_har_scatter(forecasts).save("figs/har_scatter.png", width=5.5, height=5.5, **size)
reporting.success("Figures saved to figs/")
