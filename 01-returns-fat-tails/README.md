# Project 1: Returns and fat tails

**Question:** are daily returns of the Ibovespa and USD/BRL normally
distributed, and how wrong is a normal VaR if they are not?

**Short answer:** no. Both assets have fat tails (Ibovespa: excess kurtosis
about 12). A normal VaR is too low at 99% for the dollar (it is breached 1.9%
of the time instead of 1%) and too high at 95% for both assets. Expected
Shortfall is about 60% larger than the 99% VaR for the Ibovespa.

## What this project covers

- Log returns and why risk models use them
- The four moments: mean, volatility, skewness, kurtosis
- Testing normality with Jarque-Bera
- Value at Risk two ways: historical simulation and parametric (normal)
- Expected Shortfall

## Files

| File | Purpose |
|------|---------|
| `risk.py` | The risk functions, implemented from scratch (Python) |
| `test_risk.py` | 17 unit tests with known answers |
| `analysis.py` | Downloads the data, builds the tables and figures (Python) |
| `r/` | R mirror, organised as an R project (`00_run_all.R`, numbered scripts, `R/` helpers, `tabs/`, `figs/`); cross-checks the Python numbers |

## How to run

```bash
pytest               # all 17 tests pass
python analysis.py   # prints the tables, saves figures/ and results/
# R mirror: open the r/ folder in your IDE and run r/00_run_all.R
#   (needs cli, janitor, dplyr, tidyr, purrr, readr, ggplot2, moments, quantmod, knitr)
```

## Method

1. Daily closing prices since 2010 for the Ibovespa (`^BVSP`) and USD/BRL
   (`BRL=X`), from Yahoo Finance (sample 2010-01-05 to 2026-10-16).
2. Log returns: `r_t = ln(P_t / P_{t-1})`.
3. Descriptive statistics and the Jarque-Bera test,
   `JB = n/6 * (S^2 + K^2/4)`, chi-squared with 2 degrees of freedom under
   normality.
4. 1-day VaR at 95% and 99%:
   - Historical: the empirical quantile of returns.
   - Parametric: `-(mu + sigma * z)`, assuming normal returns.
5. Historical Expected Shortfall: the average loss beyond the VaR.
6. Breach rate: the share of days on which the loss exceeded the normal VaR,
   compared with the expected 5% and 1%.

## Results

| | Ibovespa | USD/BRL |
|---|---:|---:|
| Observations | 4,162 | 4,369 |
| Annualised volatility | 23.1% | 16.6% |
| Skewness | -0.73 | 0.08 |
| Excess kurtosis | 11.95 | 3.62 |
| Jarque-Bera | 25,143 | 2,392 |
| JB p-value | < 0.0001 | < 0.0001 |

| Asset | Conf. | Historical VaR | Normal VaR | Hist / Normal | Historical ES | Normal-VaR breach rate (expected) |
|---|---|---:|---:|---:|---:|---:|
| Ibovespa | 95% | 2.23% | 2.37% | 0.94 | 3.26% | 4.2% (5%) |
| Ibovespa | 99% | 3.44% | 3.36% | 1.02 | 5.54% | 1.2% (1%) |
| USD/BRL | 95% | 1.61% | 1.70% | 0.95 | 2.39% | 4.2% (5%) |
| USD/BRL | 99% | 2.87% | 2.41% | 1.19 | 3.59% | 1.9% (1%) |

The R script reproduces every number above to four decimals.

Worst days. Ibovespa: 2020-03-12 (-16.0%), 2020-03-16 (-15.0%), 2020-03-09
(-13.0%), 2020-03-18 (-10.9%), 2017-05-18 (-9.2%, the JBS tape). USD/BRL:
2012-01-30, 2020-05-11, 2015-09-25, 2018-06-11, 2022-10-04 (all between
-4.7% and -6.4%).

Figures: `figures/hist_*.png` (histogram vs normal on a log scale) and
`figures/qq_*.png` (QQ plots).

## Answers

1. **Why log returns?** They add across time (the multi-day return is the
   sum of daily ones) and are symmetric in gains and losses. For daily
   returns of 1% the log and simple versions differ by about 0.005
   percentage points, so it matters little; it matters for large moves
   (-16% log is -14.8% simple) and for long horizons.
2. **JB p-value near zero** means normality is rejected, and with 4,000+
   observations the test is powerful enough to reject tiny departures. It
   does not say how bad the departure is (the kurtosis and the QQ plot do),
   nor which alternative is right.
3. **Why does the sign of the error flip?** Fat tails put more mass far out
   and, for the same variance, less mass in the shoulders. The 95% quantile
   sits in the shoulder, where the normal is too fat, so normal VaR is too
   high. The 99% quantile is far enough out for the tail mass to dominate,
   so normal VaR is too low. The effect is clear for USD/BRL; for the
   Ibovespa the 99% point is near the crossover (ratio 1.02), but the
   damage shows up in ES, 5.5% against the normal VaR of 3.4%.
4. **Historical VaR assumes** that the future looks like the sampled past
   (stationary, i.i.d.). It fails after regime changes, in calm samples that
   exclude crises, and it reacts slowly to volatility clusters (see
   project 2).
5. **VaR to ES under FRTB:** VaR ignores how bad losses are beyond the
   threshold and is not subadditive, so it can penalise diversification. ES
   measures the tail and is coherent.
6. **Fatter tails:** the Ibovespa (kurtosis 11.9 against 3.6), with the
   worst days clustered in March 2020 (COVID-19) and May 2017.
