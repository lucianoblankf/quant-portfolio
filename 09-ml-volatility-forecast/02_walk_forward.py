"""02: walk-forward out-of-sample forecasts (expanding window, refit every 63 days)."""

import pandas as pd

from src import config, models, reporting, volml

reporting.section("02 Walk-forward")

dataset = pd.read_parquet("data/processed/dataset.parquet")
features = [c for c in dataset if c.startswith("f_")]

forecasts = volml.walk_forward(
    dataset,
    models.fitted_models(),
    models.feature_sets(features),
    start=config.START_ROW,
    refit=config.REFIT_EVERY,
    h=config.HORIZON,
)
# Benchmarks that need no fitting
forecasts["Naive (yesterday)"] = dataset.loc[forecasts.index, "f_logrv_1"]
forecasts["EWMA 0.94"] = volml.ewma_forecast(dataset["rv"], 0.94).loc[forecasts.index]
forecasts.to_parquet("data/processed/forecasts.parquet")

reporting.success(
    f"Out-of-sample: {len(forecasts)} days, {forecasts.index.min().date()} to {forecasts.index.max().date()}"
)
