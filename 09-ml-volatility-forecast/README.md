# Project 9: Machine learning vs HAR for volatility forecasting

**Question:** can random forests and gradient boosting forecast Ibovespa
volatility better than the simple, linear HAR model?

**Short answer:** no. Out of sample, the HAR model with a few extra features
(Ridge) is the most accurate, plain HAR is a close second, and the two tree
models are statistically indistinguishable from HAR over the full period but
fail badly in the COVID crash, because trees cannot predict values beyond
what they saw in training. The useful extra information is a leverage feature
(recent negative returns), not model complexity.

## What this project covers

- A volatility proxy from the daily high-low range (Parkinson estimator) and a
  target that is the log of the average variance over the next 5 days
- Features built only from past data, with a test that proves there is no look-ahead
- Walk-forward evaluation: expanding window, refit every 63 days, training rows
  whose target overlaps the test period removed
- Six models: naive, EWMA, HAR, HAR with extra features (Ridge), random forest,
  gradient boosting
- Loss functions suited to volatility (MSE on log variance, QLIKE), the
  Mincer-Zarnowitz R-squared and the Diebold-Mariano test with overlap-robust
  variance
- Permutation feature importance

## Files

| File | Purpose |
|------|---------|
| `volml.py` | Parkinson variance, dataset builder, walk-forward, QLIKE, MZ R2, Diebold-Mariano |
| `test_volml.py` | 8 tests: estimator unbiased on Brownian paths, no look-ahead in features, walk-forward uses no future targets, loss and DM behave |
| `analysis.py` | Data, models, tables, figures |

```bash
pytest
python analysis.py     # first run downloads ^BVSP and BRL=X from Yahoo Finance
```

## Data and setup

Ibovespa daily open, high, low, close, 2010-04 to 2026-10 (4,098 days after
building features) and USD/BRL close. Nine features: log variance averaged over
1, 5, 22 and 66 days, absolute return, return, the 5-day sum of negative
returns (leverage effect), the overnight gap, and the 5-day mean absolute
USD/BRL return. The first forecast is made after 750 days; out of sample there
are 3,343 days (2013-04 to 2026-10).

## Results

Full out-of-sample period:

| Model | MSE (log) | QLIKE | MZ R-squared |
|---|---:|---:|---:|
| Naive (yesterday's variance) | 0.737 | 0.579 | 0.29 |
| EWMA 0.94 | 0.308 | 0.177 | 0.47 |
| HAR (OLS) | 0.266 | 0.169 | 0.50 |
| **HAR + extras (Ridge)** | **0.253** | **0.161** | **0.53** |
| Random forest | 0.293 | 0.218 | 0.45 |
| Gradient boosting | 0.299 | 0.214 | 0.44 |

Diebold-Mariano on QLIKE against HAR: the naive model is worse (p < 0.0001);
EWMA, Ridge, random forest and boosting are not statistically different from HAR
(p between 0.13 and 0.17). The improvement from the extra features is
small in numbers and not significant on this test.

Splitting the sample shows where the models differ:

| QLIKE | Calm periods | COVID window (2020-02-15 to 2020-06-30) |
|---|---:|---:|
| Naive | 0.574 | 0.760 |
| EWMA | 0.147 | 1.247 |
| HAR | 0.141 | 1.152 |
| HAR + extras (Ridge) | 0.139 | 0.953 |
| Random forest | 0.144 | 2.866 |
| Gradient boosting | 0.148 | 2.586 |

In calm periods all the fitted models are within 7% of each other. In the crash the
tree models are two to three times worse than HAR: volatility reached levels
never seen in the training sample, and a tree can only predict an average of
the values it has seen (the most likely explanation; the experiment does not
isolate it). Linear models extrapolate. (The naive model is the
best in this short window on QLIKE, because in a regime change yesterday's
volatility is the best guide; it is far worse everywhere else.)

HAR coefficients (full sample): 0.08 on the 1-day, 0.32 on the 5-day and 0.39
on the 22-day average, so 0.70 of the total 0.78 sits on the weekly
and monthly components: volatility is persistent and slowly moving.

Permutation importance for boosting (rise in MSE when a feature is shuffled):
5-day log variance 0.028, 22-day 0.022, 1-day 0.013, **5-day sum of negative
returns 0.010**, absolute return 0.006; the USD/BRL feature, the 66-day average,
the signed return and the overnight gap are close to zero (0.002 or less).

Figures: `figures/forecast_covid.png`, `figures/accuracy_and_importance.png`,
`figures/har_scatter.png`.

## Answers

1. **Why is the ML so poor in the crash?** Trees partition the feature space and
   predict the average of the training targets in each cell, so they cap out at the
   highest volatility they have seen. March 2020 was far above the previous
   maximum in the 2010-2019 training data.
2. **What would help?** Predict a ratio to a trend (HAR forecast) and let the tree
   model only the correction; train with a longer sample including earlier crises; or
   use a model that extrapolates (linear, neural network with linear skip).
3. **Is the Ridge result real?** It is the best fitted model in every period, and
   the leverage feature carries economic meaning, but the DM test does not call
   it significant (p = 0.14). Reported as it is: a small, plausible gain.
4. **Why QLIKE and not just MSE?** Variance forecasts are noisy and the loss
   should not be dominated by a few extreme days. QLIKE ranks the forecasts
   consistently even when the proxy is noisy, and punishes under-prediction, the costly
   error in risk management, more than over-prediction.
5. **Limits.** A range-based proxy instead of intraday realised variance;
   one market; forecasts of log variance are used as variance forecasts with no bias
   correction (the models are compared on the same footing); tuning was minimal
   and fixed in advance, so the ML models might do better with more care,
   but a result that depends on that care is also worth little.
