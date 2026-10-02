# Project 1: Returns and fat tails

**Question:** are daily returns of the Ibovespa and USD/BRL normally
distributed, and how wrong is a normal VaR if they are not?

## What this project covers

- Log returns and why risk models use them
- The four moments: mean, volatility, skewness, kurtosis
- Testing normality with Jarque-Bera
- Value at Risk two ways: historical simulation and parametric (normal)
- Expected Shortfall

## Files

| File | Purpose |
|------|---------|
| `risk.py` | The risk functions, implemented from scratch |
| `test_risk.py` | Unit tests with known answers |
| `analysis.py` | Downloads the data, builds the tables and figures |

## How to run

```bash
pytest               # all tests should pass
python analysis.py   # prints the tables, saves figures to figures/
```

## Method

1. Daily closing prices since 2010 for the Ibovespa (`^BVSP`) and USD/BRL
   (`BRL=X`), from Yahoo Finance.
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

_To be written once the analysis runs on real data: the statistics table,
the VaR table, the two figures per asset, and a short answer to each
question below._

## Questions to answer

1. Why log returns rather than simple returns? When is the difference
   between them large enough to matter?
2. The Jarque-Bera p-value is essentially zero. What does that tell you,
   and what does it not tell you?
3. With fat tails, the normal VaR is too low at 99% but too high at 95%.
   Why does the sign of the error flip?
4. Historical VaR needs no distribution assumption. What does it assume
   instead, and when does that assumption fail?
5. Why did regulators move from VaR to Expected Shortfall under FRTB?
6. Which of the two assets has fatter tails, and can you name the dates
   behind its worst days?

## R mirror

Reproduce the statistics and VaR tables in R (`quantmod` or `tidyquant` for
the data, `moments` for skewness and kurtosis) in `analysis.R`, and check
that the numbers match the Python output.
