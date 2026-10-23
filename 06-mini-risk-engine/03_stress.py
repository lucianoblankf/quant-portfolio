"""03: historical and hypothetical stress tests."""

import numpy as np
import pandas as pd

from src import data, reporting
from src import engine as eng

reporting.section("03 Stress tests")

returns, yields, pf = data.load_processed()

worst_day, pnl_day = eng.worst_window(pf, returns, 1)
worst_week, pnl_week = eng.worst_window(pf, returns, 5)
equities_down = {name: np.log(0.7) for name in pf.equity}
combined = {**{name: np.log(0.75) for name in pf.equity}, "usdbrl": np.log(1.15), "rate": 0.025}

scenarios = {
    "Worst 1 day in sample": (str(worst_day.date()), pnl_day),
    "Worst 5-day window in sample": (str(worst_week.date()), pnl_week),
    "Equities -30%": ("hypothetical", eng.stress(pf, equities_down)),
    "USD/BRL +20%": ("hypothetical", eng.stress(pf, {"usdbrl": np.log(1.2)})),
    "Rates +300 bp": ("hypothetical", eng.stress(pf, {"rate": 0.03})),
    "Combined: equities -25%, USD +15%, rates +250 bp": ("hypothetical", eng.stress(pf, combined)),
}
stress = pd.DataFrame(
    [{"scenario": name, "date": when, "pnl": pnl, "pnl_pct": pnl / pf.value} for name, (when, pnl) in scenarios.items()]
)
reporting.save_table(stress, "stress")
reporting.show_table(stress, "Stress tests")
