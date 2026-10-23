# Project 6: A mini risk engine

**Question:** for a small multi-asset Brazilian portfolio, how much can we lose
in a day, where does the risk come from, what happens in a crisis, and does
the model hold up when tested?

**Short answer:** the 99% one-day VaR of a R$ 1.2 million portfolio is between
R$ 28 thousand and R$ 35 thousand (2.3% to 2.9%) by the methods that use the
whole sample, but only R$ 17.8 thousand (1.5%) using the last 500 days, because
the March 2020 crash has left the window. One stock, PETR4, is 21% of the
portfolio and 43% of the risk. The worst week in the sample (March 2020) would
have cost 21.7% of the portfolio.

## What this project covers

- A `Portfolio` class that revalues positions under any scenario (stocks and
  FX linearly, a zero-coupon bond by exact repricing so convexity is included)
- VaR and ES by four methods: historical simulation, delta-normal (sample and
  EWMA covariance) and full-revaluation Monte Carlo with Student-t factors
- Component VaR (Euler allocation), which adds up exactly to the total
- Stress tests: historical worst day and worst week, and hypothetical scenarios
- A rolling out-of-sample backtest with the Kupiec test and the Basel traffic light

## Files

| Path | Purpose |
|------|---------|
| `00_run_all.py` | Runs the tests, then the numbered scripts in order |
| `01_get_data.py` | Raw prices and Tesouro Direto file (downloaded once), factor returns |
| `02_var_es.py` | VaR and ES by four methods, component VaR |
| `03_stress.py` | Historical and hypothetical stress tests |
| `04_backtest.py` | Rolling out-of-sample backtest, Kupiec, Basel traffic light |
| `05_figures.py` | Figures in `figs/` (plotnine, 300 dpi) |
| `src/engine.py` | Portfolio, P&L, VaR/ES methods, component VaR, stress, rolling VaR, Kupiec |
| `src/data.py`, `src/plots.py`, `src/reporting.py`, `src/config.py` | Data, plots, console and table export, positions and parameters |
| `tests/test_engine.py` | 15 tests: exact revaluation, methods agree on normal data, components add to total, homogeneity, diversification, MC tail, stress, Kupiec |
| `tabs/` | Result tables as `.csv`, `.tex` and `.html` |

Open the project folder in your IDE (working directory = project root) and run
`00_run_all.py`. Positions, window sizes and seeds are in `src/config.py`. Needs internet the
first time (yfinance and Tesouro Transparente), then uses `data/`. Needs: numpy, pandas, scipy,
plotnine, pyjanitor, rich, pyarrow, jinja2, yfinance, pytest. Factor names in the tables are
lowercase (`petr4`, `vale3`, `itub4`, `wege3`, `usdbrl`, `rate`).

## Portfolio and data

R$ 1,200,000: PETR4 250k, VALE3 200k, ITUB4 200k, WEGE3 100k, a USD position of
150k and a 3-year pre-fixed zero-coupon bond of 300k (zero yield today
12.69%, Tesouro Direto data). Risk factors: daily log returns of the four stocks
and USD/BRL (Yahoo Finance) and the daily change of the 3-year zero yield. 2,859
common days, 2015-03 to 2026-10. The portfolio is held fixed at today's weights
over the history: the backtest tests the model on this portfolio, not on past
trading.

## Results

1-day VaR and ES, R$ and as a fraction of the portfolio:

| Method | VaR 95% | ES 95% | VaR 99% | ES 99% |
|---|---:|---:|---:|---:|
| Historical, last 500 days | 12.0k (1.00%) | 15.5k | 17.8k (1.48%) | 19.6k |
| Historical, full sample | 18.9k (1.57%) | 30.4k | 33.8k (2.82%) | 52.7k |
| Delta-normal, sample covariance | 22.9k (1.91%) | 28.7k | 32.4k (2.70%) | 37.1k |
| Delta-normal, EWMA 0.94 | 19.8k (1.65%) | 24.9k | 28.0k (2.34%) | 32.1k |
| Monte Carlo, t(5) factors | 21.2k (1.76%) | 30.0k | 34.7k (2.89%) | 45.6k |

- The method matters less than the data window: the 500-day historical VaR is
  half the full-sample one because those 500 days contain no crisis.
- At 99% the expected shortfall of the historical full-sample method (52.7k)
  is 56% above its VaR; the normal model puts it at 15% above: the fat-tail
  effect of project 1, now at portfolio level. The t(5) Monte Carlo, with the
  same covariance, gets halfway there (ES 45.6k).
- At 95% the normal VaR (22.9k) is above the historical one (18.9k): same
  sign flip as in project 1.

Where the risk comes from (delta-normal, 99%, total R$ 32.4k):

| Factor | Exposure | Contribution | Share |
|---|---:|---:|---:|
| PETR4 | 250k | 14.1k | 43% |
| VALE3 | 200k | 8.6k | 26% |
| ITUB4 | 200k | 6.3k | 20% |
| WEGE3 | 100k | 2.3k | 7% |
| 3y rate (bond) | 300k | 0.65k | 2% |
| USD/BRL | 150k | 0.40k | 1% |

The sum of stand-alone VaRs is 48.7k; diversification takes the portfolio
VaR down to 32.4k (33% less). The bond is 25% of the portfolio but only 2% of
the risk, and the USD position 13% and 1%. Caveat: the 3-year yield comes
from a morning snapshot, interpolated between bonds, so its daily changes are
noisy but not very volatile; project 4 discusses the same data issue.

Stress tests:

| Scenario | P&L | % of portfolio |
|---|---:|---:|
| Worst day in the sample (2020-03-09) | -128.6k | -10.7% |
| Worst 5 days (ending 2020-03-12) | -260.1k | -21.7% |
| Equities -30% | -225.0k | -18.8% |
| USD/BRL +20% | +30.0k | +2.5% |
| Rates +300 bp | -22.7k | -1.9% |
| Combined: equities -25%, USD +15%, rates +250 bp | -184.1k | -15.3% |

The worst day in the sample is about 4 times the full-sample 99% delta-normal VaR; the worst week
about 8 times, which is why a stress test complements VaR.

Backtest of the 99% VaR (2,359 days, expected 23.6 breaches):

| Method | Breaches | Kupiec p-value | Last 250 days |
|---|---:|---:|---|
| Historical (500d) | 19 | 0.33 | 2 (green) |
| Delta-normal (rolling covariance) | 20 | 0.45 | 2 (green) |
| EWMA | 33 | 0.07 | 2 (green) |

None is rejected at 5%, but EWMA comes closest (33 breaches against 23.6
expected, p = 0.07): reacting quickly to volatility did not pay here, and the
two slower models were better calibrated on this portfolio.

Figures: `figs/pnl_distribution.png`, `component_var.png`, `backtest.png`,
`stress.png`.

## Answers

1. **Why do the component VaRs add up?** VaR under a normal model is
   homogeneous of degree one in the positions, so by Euler's theorem the total
   equals the sum of position times marginal VaR.
2. **Why is full-revaluation Monte Carlo useful if it is slower?** It keeps
   non-linear payoffs (here the bond's convexity) and fat tails; delta-normal
   cannot.
3. **Which VaR should be reported?** None alone. The 500-day window says 17.8k,
   the full sample 33.8k; the regulator-style answer is to report ES and
   stress next to VaR and show the sensitivity to the window.
4. **Limits.** Fixed portfolio, one day, no liquidity horizon, one rate factor
   (the whole curve moves in parallel) and no option positions.
