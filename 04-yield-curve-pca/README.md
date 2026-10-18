# Project 4: PCA of the yield curve

**Question:** how many independent forces move the Brazilian pre-fixed yield
curve, and what do they look like?

**Short answer:** essentially one. A parallel "level" move explains 95% of the
variance of weekly yield changes, "slope" adds 4.1% and "curvature" 0.7%. Three
factors rebuild the weekly changes to within 0.7 bp.

## What this project covers

- Building a constant-maturity zero curve (1, 2, 3, 5 years) from the
  individual LTN bonds, by interpolating yields between the two bonds around
  each tenor
- PCA on the covariance matrix of weekly yield changes (in bp, so tenors
  share the same unit)
- Reading the loadings as level, slope and curvature, and checking them against
  simple measures
- Stability of the factor structure across two sub-periods
- Stress scenarios built in factor space (+/- 3 standard deviations of each factor)

## Files

| Path | Purpose |
|------|---------|
| `00_run_all.R` | Runs everything in order |
| `01_get_data.R` | Downloads the raw Tesouro Direto file once, keeps the LTN records |
| `02_curve.R` | Constant-maturity zero curve |
| `03_pca.R` | PCA, sub-periods, stress scenarios, reconstruction error; tables to `tabs/` |
| `04_figures.R` | `curve_history.png`, `loadings.png`, `scree.png` in `figs/` (300 dpi) |
| `R/curve.R`, `R/pca.R`, `R/plots.R`, `R/tables.R` | Helper functions by topic |

Open this folder as the working directory in your IDE and run `00_run_all.R`.
Needs: cli, janitor, dplyr, tidyr, purrr, readr, ggplot2, scales, knitr. The raw file
`data/raw/tesouro_direto.csv` is downloaded on first run and not versioned.

## Data

"Tesouro Prefixado" (LTN, zero-coupon) morning buy yields from
[Tesouro Transparente](https://www.tesourotransparente.gov.br), 2004-2026.
A 5-year constant-maturity point needs a bond maturing beyond five years, and
the Treasury did not always offer one, so the usable curve has 2,391 trading days
(2015-03 to 2026-10) with no data in 2021 and gaps in 2022-2023. Changes that
span a gap longer than 10 days are discarded, leaving 496 weekly changes. The
quotes are a morning snapshot, which is why changes are measured weekly and not
daily.

## Results

| Factor | Variance share | Weekly s.d. (bp) |
|---|---:|---:|
| PC1 (level) | 95.1% | 52.7 |
| PC2 (slope) | 4.1% | 11.0 |
| PC3 (curvature) | 0.7% | 4.4 |
| PC4 | 0.06% | 1.4 |

Loadings:

| Tenor | PC1 | PC2 | PC3 |
|---|---:|---:|---:|
| 1y | 0.33 | -0.66 | -0.66 |
| 2y | 0.52 | -0.37 | 0.46 |
| 3y | 0.56 | 0.08 | 0.39 |
| 5y | 0.56 | 0.65 | -0.45 |

- PC1 has the same sign everywhere and is larger at longer tenors: a
  parallel shift, with long rates moving more than the 1-year rate. Its
  score has correlation 0.999 with the change in the average yield.
- PC2 is negative at 1y and positive at 5y: a steepening or flattening. Its
  correlation with the change in the 5y-1y spread is 0.76.
- PC3 has the belly (2y, 3y) against the wings: curvature. Its correlation
  with the change in `2*y2 - y1 - y3` is only 0.52, because with four
  tenors the third component is also absorbing noise from the quote
  snapshots, so read it as indicative.
- Stability: before 2019 PC1 explains 94.4% (188 weeks), from 2019 on 95.7%
  (308 weeks), with almost identical weekly volatility (53 vs 52 bp).

Stress scenarios on the latest curve (return of a zero-coupon bond held at each
tenor, in %):

| Shock | 1y | 2y | 3y | 5y |
|---|---:|---:|---:|---:|
| PC1 +3 sd (rates up 51 to 89 bp) | -0.45 | -1.44 | -2.33 | -3.81 |
| PC1 -3 sd | +0.46 | +1.47 | +2.40 | +3.99 |
| PC2 +3 sd (steepening) | +0.19 | +0.22 | -0.07 | -0.94 |
| PC3 +3 sd | +0.08 | -0.11 | -0.14 | +0.26 |

## Answers

1. **Why PCA on changes and not levels?** Yield levels are close to
   non-stationary and trending, so their covariance matrix is dominated by
   slow common drift. Changes are the quantities a risk model has to
   forecast.
2. **Why covariance and not correlation?** All variables are in bp. Using the
   correlation matrix would give the quiet 1y point the same weight as the
   volatile 5y point and understate the level factor.
3. **What does 95% in one factor mean for hedging?** A single DV01-style
   hedge neutralises most of the risk of a curve position, but the residual 5%
   (slope) is what a curve trade is actually about.
4. **What limits this analysis?** Four tenors, a data set with an incomplete
   long end, and morning quotes. A DI1 futures curve with 10 or more vertices
   would give cleaner factors, especially for curvature.
