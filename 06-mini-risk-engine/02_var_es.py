"""02: 1-day VaR and ES by four methods, and component VaR."""

import numpy as np
import pandas as pd
from scipy import stats

from src import config, data, reporting
from src import engine as eng

reporting.section("02 VaR and ES")

returns, yields, pf = data.load_processed()
reporting.info(f"Portfolio value R$ {pf.value:,.0f}; 3y zero yield today {pf.bond_yield:.2%}")

cov_sample = returns[pf.factors].cov()
cov_ewma = eng.ewma_cov(returns[pf.factors], config.EWMA_LAMBDA)

rows = []
for alpha in config.ALPHAS:
    results = {
        f"Historical ({config.HIST_WINDOW}d)": eng.historical(pf, returns, config.HIST_WINDOW, alpha),
        "Historical (full sample)": eng.historical(pf, returns, None, alpha),
        "Delta-normal (full sample cov)": eng.delta_normal(pf, cov_sample, alpha),
        f"Delta-normal (EWMA {config.EWMA_LAMBDA})": eng.delta_normal(pf, cov_ewma, alpha),
        f"Monte Carlo t({config.MC_NU}), sample cov": eng.monte_carlo_t(
            pf, cov_sample, nu=config.MC_NU, n=config.MC_SIMULATIONS, alpha=alpha, seed=config.SEED_MONTE_CARLO
        ),
    }
    for method, (var, es) in results.items():
        rows.append(
            {"method": method, "confidence": alpha, "var": var, "var_pct": var / pf.value, "es": es, "es_pct": es / pf.value}
        )
var_es = pd.DataFrame(rows)
reporting.save_table(var_es, "var_es")
reporting.show_table(var_es, "1-day VaR and ES (R$)")

# Component VaR (delta-normal, 99%, sample covariance) and diversification benefit
components = eng.component_var(pf, cov_sample, 0.99)
total = components["component_var"].sum()
z = stats.norm.ppf(0.99)
stand_alone = pd.Series(
    {f: abs(e) * np.sqrt(cov_sample.loc[f, f]) * z for f, e in pf.exposures().items()}
).sum()
reporting.save_table(components.reset_index(names="factor"), "component_var")
reporting.show_table(components.reset_index(names="factor"), "Delta-normal 99% VaR decomposition (sample covariance)")
reporting.info(
    f"Sum of components {total:,.0f}; sum of stand-alone VaRs {stand_alone:,.0f}; "
    f"diversification benefit {1 - total / stand_alone:.0%}"
)

# P&L of the last 500 days of factor moves, for the distribution figure
pnl = pd.Series(pf.pnl(returns[pf.factors].tail(config.HIST_WINDOW)), name="pnl")
pnl.to_frame().to_parquet("data/processed/pnl_last_window.parquet")
