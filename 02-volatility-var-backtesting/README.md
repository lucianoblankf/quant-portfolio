# Project 2: Volatility and VaR backtesting

**Question:** returns have volatility clusters. Does a VaR that reacts to them
(GARCH, EWMA) pass a backtest where a static historical VaR does not?

**Short answer:** at 95% every model passes. At 99%, where it matters, the
historical, normal and EWMA models fail the Kupiec test or the conditional
coverage test, while GARCH with Student-t errors passes both (29 breaches vs
31.6 expected). Static models also breach in clusters, which is exactly what
a risk manager cannot afford.

## What this project covers

- Evidence of volatility clustering (Ljung-Box on squared returns, ACF)
- GARCH(1,1) written from scratch: filter, Gaussian and Student-t likelihood,
  maximum likelihood with `optim`, persistence and half-life
- EWMA (RiskMetrics, lambda = 0.94)
- A rolling out-of-sample VaR with periodic re-estimation (1,000-day window,
  refit every 21 days, no look-ahead)
- Backtests: Kupiec proportion of failures, Christoffersen independence,
  conditional coverage, Basel traffic light

## Files

| File | Purpose |
|------|---------|
| `garch_var.R` | Models, rolling forecasts and backtests, no external GARCH package |
| `tests.R` | Checks with known answers (parameter recovery on simulated GARCH, tests behave as theory says) |
| `analysis.R` | Full analysis on the Ibovespa, writes `results/` and `figures/` |

```bash
Rscript tests.R
Rscript analysis.R
```

Data: Ibovespa daily closes since 2010 (Yahoo Finance via `quantmod`), cached
in `data/`. Packages: `ggplot2`, `moments`, `tseries`, `quantmod`.

## Results

**Clustering.** Ljung-Box on returns and on squared returns (10 lags) both
reject with p below 0.0001; the squared returns have a long, slowly decaying
ACF (`figures/acf_squared_returns.png`).

**GARCH(1,1), full sample (2010-2026).**

| Errors | alpha | beta | alpha + beta | Half-life | nu | AIC |
|---|---:|---:|---:|---:|---:|---:|
| Normal | 0.074 | 0.899 | 0.973 | 25 days | | 14,032 |
| Student-t | 0.060 | 0.921 | 0.981 | 36 days | 8.1 | 13,896 |

The t model wins on AIC by 136 points and estimates 8 degrees of freedom: fat
tails remain even after conditioning on volatility.

**Out-of-sample backtest** (3,162 days, 2014-01-21 to 2026-10-16). Breaches
and p-values (Kupiec / Christoffersen independence / conditional coverage):

| Model | 95%: breaches (exp. 158) | Kupiec p | 99%: breaches (exp. 31.6) | Kupiec p | Indep. p | Cond. cov. p |
|---|---:|---:|---:|---:|---:|---:|
| Historical 250d | 165 | 0.58 | 43 | 0.054 | 0.0002 | 0.0002 |
| Normal 250d | 147 | 0.36 | 51 | 0.0015 | 0.0013 | 0.00003 |
| EWMA 0.94 | 162 | 0.75 | 49 | 0.004 | 0.21 | 0.007 |
| GARCH-normal | 141 | 0.16 | 39 | 0.20 | 0.32 | 0.27 |
| GARCH-t | 151 | 0.56 | 29 | 0.63 | 0.46 | 0.68 |

Basel traffic light over the last 250 days at 99%: all green except the
normal 250-day model (7 breaches, yellow). In 2020 alone the static models
breached 9 times in 248 days against 2.5 expected; the GARCH-t breached 6
times, two of them on 9 and 12 March, the first days of the crash (a shock's
first days cannot be forecast by any model that learns from the past).

`figures/var_covid.png` shows the mechanism: the GARCH-t VaR jumps within days
of the March 2020 shock and decays as volatility normalises, while the
250-day historical VaR reacts late and stays inflated for a year after the
crisis ended.

## Answers

1. **Why does historical VaR fail the independence test?** It reacts to a
   shock only by adding one observation to a 250-day window, so after a
   regime change breaches arrive in streaks. GARCH raises sigma the day after
   a large move.
2. **Why does Kupiec pass but independence fail for the historical VaR?**
   Kupiec only counts breaches; their total (43 vs 32) is borderline. The
   problem is when they happen, which only the independence test sees.
3. **Why a t distribution on top of GARCH?** GARCH explains the clustering,
   but standardised residuals are still fat-tailed (nu is about 8). With
   normal errors the 99% quantile is too close to zero.
4. **Is "more breaches than expected" always bad?** Too many is a model
   failure; too few (GARCH-t at 99%: 0.92% vs 1%) means capital is idle.
   Both are rejected by the Kupiec test in the extreme.
5. **Limits.** One asset, zero conditional mean, GARCH(1,1) symmetric (no
   leverage effect; a GJR/EGARCH extension is the natural next step), and 1-day
   horizon only.
