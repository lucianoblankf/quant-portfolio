# Project 8: Selic, inflation and the Taylor rule

**Question:** how does the Banco Central do Brasil set Selic in response to
inflation and the output gap, and what does a Selic shock do to inflation?

**Short answer:** Selic is explained almost entirely by its own past (smoothing
coefficient 0.97) and then by inflation and the output gap, with a long-run
inflation coefficient of about 1.7, consistent with the Taylor principle
(rejecting "equal to 1" is not possible, p = 0.44). The rule is not stable:
two structural breaks (2006-10 and 2017-11). A Selic shock raises measured
inflation for about a year (a "price puzzle") before pushing it down; the
fall at 24 months is not statistically distinguishable from zero.

## What this project covers

- Unit-root and stationarity tests (ADF and KPSS together)
- A Taylor rule by OLS with Newey-West (HAC) standard errors, static and with
  interest-rate smoothing, and the implied long-run coefficients
- Testing the Taylor principle with a Wald test on a linear restriction
- Structural stability: Bai-Perron breakpoints, supF test, sub-sample estimates
- Johansen cointegration test for Selic and inflation
- A VAR built from scratch (OLS, BIC lag choice, Granger causality, Cholesky
  impulse responses with residual-bootstrap bands)

## Files

| File | Purpose |
|------|---------|
| `var_tools.R` | VAR estimation, lag selection, Granger test, IRF with bootstrap, HP filter |
| `analysis.R` | Data download (BCB SGS API), all estimation and figures |
| `results/` | Dataset and result tables as CSV |
| `figures/` | `selic_vs_ipca.png`, `taylor_fit.png`, `irf_selic_shock.png` |

```bash
Rscript analysis.R    # needs ggplot2, tseries, sandwich, lmtest, car, strucchange, urca, jsonlite
```

## Data

Banco Central do Brasil SGS, monthly, 2003-01 to 2026-08 (284 observations):
Selic % a.a. (series 4189), IPCA 12-month (13522), IBC-Br seasonally adjusted
activity index (24364) and USD/BRL end of month (3698). The output gap is
100 x (log IBC-Br minus its HP trend, lambda = 14,400). The two-sided HP filter
uses future data, so it is a convenient proxy, not a real-time gap.

## Results

**Stationarity.** Selic is not stationary in levels (ADF p = 0.24; KPSS rejects
stationarity). IPCA 12m and the gap are stationary by ADF and not rejected by
KPSS; first differences of all are stationary.

**Taylor rule** (HAC standard errors):

| | Static | Dynamic (smoothed) |
|---|---:|---:|
| Inflation | 0.91 (t = 4.0) | 0.057 (t = 2.1) |
| Output gap | -0.07 (t = -0.3) | 0.078 (t = 3.9) |
| Lagged Selic | | 0.967 (t = 80) |
| R-squared | | 0.993 |

Long-run response of Selic implied by the dynamic model: 1.72 to inflation and 2.33 to
the gap. The static rule gives the gap the wrong sign: it ignores that Selic is
a persistent process, which the lagged-Selic term captures. The residuals still
have an AR(1) coefficient of 0.76, so the dynamic rule is a description of
the central bank's inertia, not a clean structural equation.

**Stability.** Bai-Perron selects breaks at 2006-10 and 2017-11 and the supF
test rejects constant parameters (F = 154, p < 0.0001). By sub-period:

| Period | Obs. | Inflation (short run) | Gap (short run) | Smoothing | R-squared |
|---|---:|---:|---:|---:|---:|
| 2003-2015 | 155 | 0.016 | 0.136 | 0.974 | 0.993 |
| 2016-2026 | 128 | 0.110 | 0.034 | 0.982 | 0.996 |

The central bank leaned more on inflation and less on the gap in the second
period. Long-run coefficients (0.6 and 6.2) are not reliable because the
smoothing coefficient is close to one, which makes 1 / (1 - rho) very large and
imprecise; read the short-run columns.

**Cointegration.** Johansen trace test on (Selic, IPCA 12m), with a constant: r = 0
is rejected (53.6 against 20.0), r <= 1 is not (7.6 against 9.2): one cointegrating
relation, a long-run link between the policy rate and inflation.

**VAR.** Variables (gap, IPCA 12m, Selic), levels, 2 lags (BIC), Selic ordered
last. Granger causality: Selic helps predict inflation (F = 8.7, p = 0.0002); the gap
predicts Selic (p = 0.017); inflation predicts Selic only marginally (p = 0.051);
Selic does not predict the gap (p = 0.76).

Response of IPCA 12m to a one-standard-deviation (0.23 p.p.) Selic shock: up to
+0.26 p.p. after 6 months (90% band 0.13 to 0.36), then falling; -0.11 p.p. at 24
months (band -0.22 to +0.01). Adding the exchange rate to the VAR does not remove
the early rise (peak +0.26 at month 6; -0.10 at 24 months, band -0.22 to +0.02).

## Answers

1. **Why use both ADF and KPSS?** They have opposite null hypotheses, so
   agreement is stronger evidence. Selic is I(1) by both; the inflation series
   gives ADF rejection with KPSS borderline (p = 0.08).
2. **Is a VAR in levels legitimate with a non-stationary Selic?** The VAR in
   levels is consistent even with unit roots and cointegration (Sims, Stock and
   Watson), but the Granger Wald tests are not strictly standard in that
   case; the evidence should be read as suggestive.
3. **What is the price puzzle?** After a rate rise, measured inflation rises first.
   Usual explanations: the central bank is reacting to inflation
   expectations that the VAR does not see (omitted forward-looking variable),
   or a cost channel of interest. Adding the exchange rate here was not enough;
   survey expectations (Focus) are the natural next addition.
4. **Why is the gap negative in the static rule?** Omitted dynamics: a persistent
   dependent variable and a persistent regressor produce misleading
   contemporaneous coefficients. The smoothing term fixes the sign.
5. **Limits.** Monthly Selic average (not the decision-day target), a gap
   from a filter that uses future data, a recursive identification that imposes
   that Selic does not affect the gap and inflation within the month, and
   a sample with at least two regimes.
