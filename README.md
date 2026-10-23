# Quant Portfolio

Nine self-contained projects in quantitative finance, market risk and
econometrics, built on Brazilian market data (plus SPY options for the volatility
smile). Each one implements the method from scratch, tests it against known
answers, runs it on real data, and reports what the results do and do not show,
including the negative ones.

By Luciano Blank Fonseca.

**Languages:** statistics and econometrics in **R**; numerical methods, pricing,
risk engines and machine learning in **Python**.

## Projects

| # | Project | Language | Topics | Headline result |
|---|---------|:---:|--------|-----------------|
| 1 | [Returns and fat tails](01-returns-fat-tails/) | Python + R | Log returns, moments, Jarque-Bera, historical and parametric VaR, ES | Ibovespa excess kurtosis 12; a normal VaR is breached 1.9% of the time at 99% for USD/BRL. The R version reproduces the Python numbers to 4 decimals |
| 2 | [Volatility and VaR backtesting](02-volatility-var-backtesting/) | R | GARCH(1,1) by maximum likelihood, EWMA, Kupiec, Christoffersen, Basel traffic light | At 99%, historical and normal VaR fail the backtest; GARCH-t passes (29 breaches vs 31.6 expected) |
| 3 | [The pre-fixed curve](03-treasury-curve/) | Python | Business-day/252, bootstrapping with coupon bonds, flat-forward, duration, DV01, key-rate DV01 | 8-pillar curve reprices its inputs to the cent; out-of-sample NTN-F cross-check shows 15 to 20 bp of bond-specific basis |
| 4 | [PCA of the yield curve](04-yield-curve-pca/) | R | Constant-maturity curve, PCA on yield changes, level/slope/curvature, factor stress | One factor explains 95% of the variance; three rebuild changes to 0.7 bp |
| 5 | [Option pricing](05-option-pricing/) | Python | Black-Scholes, Greeks, implied vol, Monte Carlo variance reduction, binomial tree, delta hedging, real SPY smile | Hedging error falls as 1/sqrt(n) (measured slope -0.48); SPY implied vol is 24% for low strikes vs 13% for high strikes |
| 6 | [Mini risk engine](06-mini-risk-engine/) | Python | VaR/ES by 4 methods, component VaR, stress tests, backtest | PETR4 is 21% of the portfolio and 43% of the risk; the 500-day window halves the VaR because it excludes 2020 |
| 7 | [Cointegration and pairs trading](07-pairs-cointegration/) | R | Engle-Granger, half-life, z-score strategy, out-of-sample stability | Honest negative result: 1 of 6 selected pairs still cointegrated; the strategy loses 0.9% a year after costs |
| 8 | [Selic, inflation and the Taylor rule](08-selic-ipca-taylor/) | R | HAC regression, structural breaks, Johansen, VAR from scratch, Granger, IRF | Smoothing 0.97, long-run inflation response 1.7, breaks in 2006 and 2017; the price puzzle appears in the IRF |
| 9 | [ML vs HAR for volatility](09-ml-volatility-forecast/) | Python | Walk-forward ML, QLIKE, Diebold-Mariano, permutation importance | Trees do not beat HAR and fail in the 2020 crash; a leverage feature helps the linear model |

## Data sources

- Yahoo Finance (`yfinance` in Python, `quantmod` in R): Ibovespa, USD/BRL, Brazilian stocks, SPY options
- Tesouro Transparente: Tesouro Direto prices and yields (LTN, NTN-F), used in projects 3, 4 and 6
- Banco Central do Brasil, SGS API: Selic, IPCA, IBC-Br, exchange rate (project 8)

Raw downloads are cached in each project's `data/` folder (not versioned); the
scripts fetch them on first run. Tables and figures are versioned in `results/`
and `figures/`.

## Setup

Python 3.12:

```bash
conda create -n quant python=3.12
conda activate quant
pip install -r requirements.txt
```

R 4.5 or later:

```r
install.packages(c("quantmod", "moments", "tseries", "urca", "sandwich", "lmtest",
                   "car", "strucchange", "ggplot2", "dplyr", "tidyr", "jsonlite"))
```

## Running a project

Python projects (1, 3, 5, 6, 9) follow one layout: numbered scripts in the project root,
helper modules in `src/` (one file per topic), tests in `tests/`, raw data in `data/raw/`,
processed data in `data/processed/` (parquet), tables in `tabs/` and figures in `figs/`
(plotnine, 300 dpi). Open the project folder in your IDE as the working directory and run
`00_run_all.py`, which runs the tests first and then the scripts in order.

R projects (2, 4, 7, 8 and the R version of 1, in `01-returns-fat-tails/r/`) follow one
layout: numbered scripts in the project root, helper functions in `R/` (one file per
topic), raw data in `data/raw/`, processed data in `data/processed/`, tables in `tabs/`
and figures in `figs/`. Open the project folder in your IDE as the working directory
and run `00_run_all.R`. Project 2 also has `99_tests.R` with checks on known answers.

Test counts: project 1: 17, project 3: 13, project 5: 24, project 6: 15,
project 9: 8 (pytest); project 2: 8 checks (`99_tests.R`).

## How the projects are built

1. Write the method from scratch, with the formulas in the docstring.
2. Test it against a known answer (textbook values, closed forms, simulated data
   with known parameters) before looking at any real data.
3. Apply it to real data with a design that separates estimation from
   evaluation (rolling windows, formation/trading split, walk-forward).
4. Report the result as found. Several projects end with a finding that is
   not flattering to the method, and the README says so.
