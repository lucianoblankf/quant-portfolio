# Project 7: Cointegration and pairs trading

**Question:** if two stocks passed a cointegration test in the past, can you
make money trading their spread afterwards?

**Short answer:** no, not here. 9 of 91 pairs tested cointegrated in the
formation window against about 5 expected by pure chance. Of the six pairs
selected, only one still passes the test out of sample, and a z-score strategy
on the six lost 0.9% a year after costs (Sharpe -0.11) with a 24% drawdown. The
hit rate was 60% yet the strategy lost money: the losers were larger than the
winners, the typical failure mode when a relation breaks.

This is a deliberately honest backtest: selection and trading are separated in time,
and the multiple-testing problem is shown rather than hidden.

## What this project covers

- Engle-Granger cointegration test, with the right (MacKinnon) critical values
  for a residual-based ADF
- Hedge ratio by OLS on log prices, half-life of mean reversion from an AR(1)
- Scanning many pairs and why that inflates false discoveries
- A rolling z-score trading rule with entry, exit and stop, and transaction costs
- Out-of-sample stability of the hedge ratio and the cointegration relation

## Files

| Path | Purpose |
|------|---------|
| `00_run_all.R` | Runs everything in order |
| `01_get_data.R` | Raw adjusted prices (downloaded once) and processed prices |
| `02_pair_scan.R` | Formation scan, pair selection, out-of-sample stability |
| `03_backtest.R` | Trading the selected pairs, performance tables |
| `04_figures.R` | Figures in `figs/` (300 dpi) |
| `R/pairs.R`, `R/plots.R`, `R/tables.R` | Engle-Granger, half-life, backtest, plots, table export |
| `tabs/` | Result tables as `.rds`, `.csv` and `.tex` |

Open this folder as the working directory in your IDE and run `00_run_all.R`.
Needs: cli, janitor, dplyr, tidyr, purrr, readr, ggplot2, tseries, quantmod, knitr.

## Design

- 14 liquid Brazilian stocks (dividend-adjusted closes from Yahoo Finance,
  2015-01 to 2026-10). Four tickers of the original list did not download
  and were dropped: the pair universe is the remaining 91 combinations.
- **Formation**, 2015-2019: test every pair, estimate the hedge ratio, keep
  the pairs with ADF statistic below -3.34 (5% MacKinnon value) and a
  half-life between 2 and 60 days; take the top six.
- **Trading**, 2020 onward, fixed formation hedge ratio. Spread z-score over
  the previous 60 days; enter at |z| > 2, exit at |z| < 0.5, stop at |z| > 4.
  Position is decided on yesterday's z-score. Cost: 10 bp per side on traded
  notional. Returns are on gross exposure.

## Results

**Scan (formation).** 9 of 91 pairs reject at 5% (about 5 expected by chance).
Strongest: BBDC4/BBAS3 (ADF -4.10), ABEV3/USIM5 (-4.04), ITUB4/ABEV3 (-3.81,
but half-life 281 days, so excluded).

**Do the selected pairs survive?** ADF statistic of the spread, formation vs trading
window (5% critical value -3.34):

| Pair | Formation | Trading, fixed beta | Beta formation to trading |
|---|---:|---:|---:|
| BBDC4/BBAS3 | -4.10 | -0.63 | 0.82 to 0.05 |
| ABEV3/USIM5 | -4.04 | -3.55 | 0.08 to 0.07 |
| ABEV3/WEGE3 | -3.66 | -3.30 | 0.16 to 0.22 |
| ITUB4/BBAS3 | -3.48 | -0.80 | 0.80 to 0.73 |
| VALE3/ITUB4 | -3.48 | -3.07 | 1.41 to 0.42 |
| ABEV3/SUZB3 | -3.47 | -3.14 | 0.05 to 0.12 |

Only ABEV3/USIM5 stays below the critical value. The two bank pairs, the
strongest in formation, fall apart (the BBDC4/BBAS3 hedge ratio goes from 0.82
to 0.05). The pairs that survive have a hedge ratio near zero, meaning the
"spread" is mostly one stock, not a relation between two.

**Strategy, 2020-2026, after costs.**

| Pair | Ann. return | Ann. vol | Sharpe | Max drawdown | Trades | Hit rate |
|---|---:|---:|---:|---:|---:|---:|
| BBDC4/BBAS3 | -2.3% | 10.6% | -0.21 | -35.5% | 32 | 66% |
| ABEV3/USIM5 | 0.2% | 15.9% | 0.01 | -33.3% | 29 | 66% |
| ABEV3/WEGE3 | 1.4% | 14.1% | 0.10 | -27.0% | 32 | 63% |
| ITUB4/BBAS3 | -4.0% | 8.2% | -0.49 | -33.5% | 30 | 53% |
| VALE3/ITUB4 | -2.4% | 12.6% | -0.19 | -37.4% | 26 | 50% |
| ABEV3/SUZB3 | 1.6% | 17.1% | 0.09 | -33.7% | 29 | 62% |
| **Equal-weight portfolio** | **-0.9%** | **8.4%** | **-0.11** | **-23.8%** | 178 | 60% |

By sub-period the portfolio Sharpe is 0.27 (2020-21), 0.12 (2022-23) and -0.65
(2024 on): the relation decays as time passes since formation.

Figures: `figures/spread_top_pair.png` (the best spread stops being stationary
after formation), `figures/equity_curve.png`, `figures/adf_scan.png`.

## Answers

1. **Why not the ordinary ADF p-value on the residual?** The residual comes
   from a regression chosen to make it look stationary, so the usual
   Dickey-Fuller distribution is too forgiving. MacKinnon critical values
   are more demanding (-3.34 against -2.86 at 5%).
2. **What is the multiple-testing problem?** With 91 pairs, 4 or 5 will pass a
   5% test by luck. The observed 9 is only a little above that, so most
   "discoveries" are probably noise. A Bonferroni-style correction demands a far
   stricter threshold than 5%.
3. **Why a 60% hit rate and negative returns?** Reversion trades pay small
   amounts often and lose large amounts when the spread keeps going
   (negative skew). The stop-loss caps a loss but crystallises it.
4. **What would make this better?** Many more candidate pairs with a
   same-sector prior (economic reason for the link, not only statistical),
   periodic re-estimation of the hedge ratio (Kalman filter), and a regime
   filter. Both bank pairs show why: a fixed beta is a bet that the
   relation is constant.
5. **Caveats.** Single formation/trading split; costs are an approximation
   with no borrow fee for the short leg, which in Brazil is not negligible
   and would make the results worse.
