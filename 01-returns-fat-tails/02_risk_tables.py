"""02: descriptive statistics, Jarque-Bera, VaR / ES tables and worst days."""

import pandas as pd

from src import data, reporting, risk

reporting.section("02 Risk tables")

ALPHAS = (0.95, 0.99)

returns = pd.read_parquet("data/processed/returns.parquet")
labels = data.ASSET_LABELS.set_index("asset")["label"]

stats_rows, var_rows = [], []
for asset, group in returns.groupby("asset"):
    r = group["log_return"].to_numpy()
    jb, p_value = risk.jarque_bera(r)
    stats_rows.append({"asset": asset, **risk.summary_stats(r), "jarque_bera": jb, "jb_p_value": p_value})
    for alpha in ALPHAS:
        hist_var, param_var = risk.historical_var(r, alpha), risk.parametric_var(r, alpha)
        var_rows.append(
            {
                "asset": asset,
                "confidence": alpha,
                "historical_var": hist_var,
                "parametric_var": param_var,
                "hist_over_param": hist_var / param_var,
                "historical_es": risk.historical_es(r, alpha),
                "param_breach_rate": float((r < -param_var).mean()),
                "expected_breach_rate": 1 - alpha,
            }
        )

stats_tbl = pd.DataFrame(stats_rows)
var_tbl = pd.DataFrame(var_rows)
worst_days = (
    returns.sort_values("log_return")
    .groupby("asset")
    .head(5)
    .sort_values(["asset", "log_return"])
    .loc[:, ["asset", "date", "log_return"]]
)

for name, tbl in (("stats", stats_tbl), ("var", var_tbl), ("worst_days", worst_days)):
    reporting.save_table(tbl, name)

reporting.show_table(stats_tbl, "Descriptive statistics")
reporting.show_table(var_tbl, "1-day VaR and ES (fraction of position value)")
reporting.info("Five worst days (log return)")
for asset, group in worst_days.groupby("asset"):
    days = ", ".join(f"{d.date()} ({v:+.1%})" for d, v in zip(group["date"], group["log_return"]))
    reporting.console.print(f"  {labels[asset]}: {days}")
reporting.success("Tables saved to tabs/")
