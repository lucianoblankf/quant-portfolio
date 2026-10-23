"""03: accuracy (full period, calm, COVID), Diebold-Mariano tests and HAR coefficients."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src import config, models, reporting, volml

reporting.section("03 Evaluation")

forecasts = pd.read_parquet("data/processed/forecasts.parquet")
dataset = pd.read_parquet("data/processed/dataset.parquet")
order = models.MODEL_ORDER


def score(frame: pd.DataFrame) -> pd.DataFrame:
    """MSE on log variance, QLIKE and Mincer-Zarnowitz R2 for every model."""
    return pd.DataFrame(
        [
            {
                "model": name,
                "mse_log": volml.mse_log(frame["y"], frame[name]),
                "qlike": volml.qlike(frame["y"], frame[name]),
                "mz_r2": volml.mz_r2(frame["y"], frame[name]),
            }
            for name in order
        ]
    )


covid = (forecasts.index >= config.COVID_START) & (forecasts.index <= config.COVID_END)
tables = {
    "accuracy_full": score(forecasts),
    "accuracy_calm": score(forecasts[~covid]),
    "accuracy_covid": score(forecasts[covid]),
}
for name, tbl in tables.items():
    reporting.save_table(tbl, name)
reporting.show_table(tables["accuracy_full"], "Out-of-sample accuracy, full period")
reporting.show_table(tables["accuracy_calm"], f"Calm periods (excluding {config.COVID_START} to {config.COVID_END})")
reporting.show_table(tables["accuracy_covid"], f"COVID window ({config.COVID_START} to {config.COVID_END})")


# Diebold-Mariano on the per-observation QLIKE loss, each model against HAR
def qlike_loss(name: str) -> np.ndarray:
    ratio = np.exp(forecasts["y"] - forecasts[name])
    return (ratio - np.log(ratio) - 1).to_numpy()


dm_rows = []
for name in order:
    if name == "HAR (OLS)":
        continue
    stat, p_value = volml.diebold_mariano(qlike_loss(name), qlike_loss("HAR (OLS)"), h=config.HORIZON)
    verdict = "no difference"
    if p_value < 0.05:
        verdict = "better" if stat < 0 else "worse"
    dm_rows.append({"model": name, "dm_stat_vs_har": stat, "p_value": p_value, "vs_har": verdict})
dm = pd.DataFrame(dm_rows)
reporting.save_table(dm, "diebold_mariano")
reporting.show_table(dm, "Diebold-Mariano on QLIKE, each model against HAR (negative = model better)")

# HAR coefficients on the full sample
complete = dataset.dropna(subset=["y"])
har = LinearRegression().fit(complete[config.HAR_FEATURES], complete["y"])
har_coefficients = pd.DataFrame(
    {"term": ["intercept", *config.HAR_FEATURES], "estimate": [har.intercept_, *har.coef_]}
)
reporting.save_table(har_coefficients, "har_coefficients", digits=3)
reporting.show_table(har_coefficients, "HAR coefficients (full sample)", digits=3)
