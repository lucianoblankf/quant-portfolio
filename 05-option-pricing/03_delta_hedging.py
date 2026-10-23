"""03: delta hedging, hedging error by rebalancing frequency and by hedge volatility."""

import numpy as np
import pandas as pd

from src import config, reporting
from src.hedging import delta_hedge

reporting.section("03 Delta hedging")

frequency = pd.DataFrame(
    [
        {"rebalances": n, "mean": pnl.mean(), "std": pnl.std(), "std_x_sqrt_n": pnl.std() * np.sqrt(n)}
        for n in config.REBALANCES
        for pnl in [delta_hedge(n, config.SIG)]
    ]
)
slope = np.polyfit(np.log(frequency["rebalances"]), np.log(frequency["std"]), 1)[0]

wrong_vol = pd.DataFrame(
    [
        {"hedge_vol": v, "mean": pnl.mean(), "std": pnl.std()}
        for v in config.HEDGE_VOLS
        for pnl in [delta_hedge(252, v)]
    ]
)

reporting.save_table(frequency, "hedging_frequency")
reporting.save_table(wrong_vol, "hedging_vol_error")
reporting.show_table(frequency, f"Hedge vol = true vol ({config.HEDGE_PATHS:,} paths)")
reporting.info(f"log-log slope of std against rebalances: {slope:.2f} (theory: -0.5)")
reporting.show_table(wrong_vol, "Daily hedging with the wrong volatility (true vol 20%)")

# P&L samples for the distribution figure
samples = pd.concat(
    [pd.DataFrame({"pnl": delta_hedge(n, config.SIG), "rebalances": f"{n} rebalances"}) for n in (12, 252)]
)
samples.to_parquet("data/processed/hedging_pnl.parquet", index=False)
