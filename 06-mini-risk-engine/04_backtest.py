"""04: rolling out-of-sample backtest of the 99% 1-day VaR (Kupiec and Basel traffic light)."""

import pandas as pd

from src import config, data, reporting
from src import engine as eng

reporting.section("04 Backtest")

returns, yields, pf = data.load_processed()
p = 1 - config.BACKTEST_ALPHA

rows, series = [], {}
for method in ("hist", "normal", "ewma"):
    var, pnl = eng.rolling_var(pf, returns, method, config.BACKTEST_ALPHA, window=config.BACKTEST_WINDOW, lam=config.EWMA_LAMBDA)
    series[f"var_{method}"] = var
    series["pnl"] = pnl
    breaches = pnl < -var
    _, kupiec_p = eng.kupiec(int(breaches.sum()), len(breaches), p)
    last_250 = int(breaches.tail(250).sum())
    rows.append(
        {
            "method": method,
            "days": len(breaches),
            "breaches": int(breaches.sum()),
            "expected": len(breaches) * p,
            "kupiec_p": kupiec_p,
            "last_250_breaches": last_250,
            "basel_zone": "green" if last_250 <= 4 else ("yellow" if last_250 <= 9 else "red"),
        }
    )

backtest = pd.DataFrame(rows)
reporting.save_table(backtest, "backtest")
reporting.show_table(backtest, "Backtest of the 99% 1-day VaR (portfolio P&L at today's positions)")

pd.DataFrame(series).rename_axis("date").reset_index().to_parquet("data/processed/backtest_series.parquet", index=False)
