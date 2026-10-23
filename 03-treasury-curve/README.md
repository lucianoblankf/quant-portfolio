# Project 3: The pre-fixed curve (bootstrapping, pricing, DV01)

**Question:** given the prices of Brazilian pre-fixed government bonds, what is
the zero curve, and how sensitive is each bond to it?

**Short answer:** an eight-pillar curve from 0.2 to 10.1 years, built bond by
bond, reprices all eight inputs to the cent (error 0.0000). The zero rate is
13.4% at 0.2 years, dips to 12.6% at 2.2 years and rises to 12.9% at 6 to 8 years (an
inverted front end, then flat). A 2037 NTN-F loses 0.48 per 1,000 of face
for each 1 bp rise in rates, 3.2 times a 2029 LTN of the same face.

A note on the data: Brazil's DI1 futures curve is the usual choice for this
exercise, but it is not freely downloadable. The Tesouro Direto quotes (LTN and
NTN-F) are public and give a pre-fixed government curve. It is a sovereign
curve, not the swap (DI) curve, and its quotes are a morning snapshot.

## What this project covers

- Brazilian conventions: business-day/252 compounding and the ANBIMA holiday
  calendar, built from Easter
- Flat-forward interpolation (log discount factor linear in time)
- Bootstrapping with coupon bonds: each NTN-F pillar is the root of
  `PV(rate) - PU = 0`, with earlier coupons discounted on the curve so far
- Pricing an LTN (zero-coupon) and an NTN-F (10% coupon, semi-annual)
- Macaulay duration, DV01 and key-rate DV01

## Files

| Path | Purpose |
|------|---------|
| `00_run_all.py` | Runs the tests, then the numbered scripts in order |
| `01_get_data.py` | Downloads the raw Tesouro Direto file once, keeps LTN and NTN-F quotes (`data/processed/bonds.parquet`) |
| `02_bootstrap.py` | Bootstraps the curve, reprices the inputs, LTN vs NTN-F basis |
| `03_risk.py` | Duration, DV01, key-rate DV01 |
| `04_figures.py` | Figures in `figs/` (plotnine, 300 dpi) |
| `src/curve.py` | Calendar, cash flows, `Curve`, `bootstrap`, `price`, `dv01`, `key_rate_dv01` |
| `src/data.py`, `src/plots.py`, `src/reporting.py`, `src/config.py` | Data, plots, console and table export, parameters |
| `tests/test_curve.py` | 13 tests: calendar, flat-forward algebra, bootstrap round-trip, key rates sum to DV01 |
| `tabs/` | Result tables as `.csv`, `.tex` and `.html` |

Open the project folder in your IDE (working directory = project root) and run
`00_run_all.py`. To use another quote date, set `QUOTE_DATE` in `src/config.py`
(default: latest date in the file). Needs: numpy, pandas, scipy, python-dateutil,
plotnine, pyjanitor, rich, pyarrow, jinja2, pytest.

## Method

1. Tesouro Transparente gives, for each bond and date, a yield and a PU. Quote date
   2026-10-15; valuation date is the next business day (2026-10-16). Since
   2024 the published PUs only match the quoted yields when discounted from that day
   (the implied business-day difference is 0.99 on average), so that is the
   convention used here.
2. Sort the instruments by maturity. For each LTN, the pillar follows directly:
   `y = (1000 / PU)^(252 / du) - 1`. For each NTN-F with no LTN at the same maturity,
   solve for the zero rate that prices the bond given the curve to its left, using
   Brent's method.
3. When an LTN and an NTN-F share a maturity, the LTN defines the pillar and
   the NTN-F is kept as an independent cross-check.
4. DV01 is the central difference of price for a 1 bp parallel move of the zero
   rates. Key-rate DV01 bumps one pillar at a time; the key rates must sum to the
   parallel DV01 (tested).

## Results (2026-10-15)

| Maturity | Years | Zero rate | Forward from previous pillar |
|---|---:|---:|---:|
| 2027-01-01 | 0.21 | 13.37% | 13.37% |
| 2028-01-01 | 1.20 | 12.77% | 12.65% |
| 2029-01-01 | 2.19 | 12.64% | 12.48% |
| 2031-01-01 | 4.17 | 12.76% | 12.89% |
| 2032-01-01 | 5.17 | 12.87% | 13.33% |
| 2033-01-01 | 6.17 | 12.94% | 13.31% |
| 2035-01-01 | 8.15 | 12.95% | 12.97% |
| 2037-01-01 | 10.15 | 12.88% | 12.59% |

Repricing: the five LTNs and the NTN-Fs of 2033, 2035 and 2037 are reproduced exactly
(they define the curve). The three NTN-Fs that share a maturity with an LTN are
an out-of-sample check:

| NTN-F | Market PU | Model PU | Error | Yield vs LTN of same maturity |
|---|---:|---:|---:|---:|
| 2027 | 1,022.37 | 1,021.99 | -0.38 | -20 bp |
| 2029 | 985.80 | 983.02 | -2.78 | -15 bp |
| 2031 | 946.71 | 947.73 | +1.02 | +3 bp |

The market prices the NTN-F 2027 and 2029 0.04% and 0.28% above what the LTN curve
implies, and the 2031 below it by 0.11%. These bond-specific differences (liquidity,
demand) are not arbitrage, and show why a curve
built from one bond type is not exactly right for the other.

Risk per 1,000 of face:

| Bond | PU | Duration (yrs) | DV01 | DV01 / price |
|---|---:|---:|---:|---:|
| LTN 2029 | 770.85 | 2.19 | 0.150 | 1.94 bp |
| LTN 2032 | 534.47 | 5.17 | 0.245 | 4.58 bp |
| NTN-F 2029 | 983.02 | 1.96 | 0.171 | 1.74 bp |
| NTN-F 2033 | 915.16 | 4.52 | 0.367 | 4.01 bp |
| NTN-F 2037 | 877.99 | 6.11 | 0.475 | 5.42 bp |

Key-rate DV01 shows where the risk sits: the LTNs concentrate it all in one pillar;
the NTN-F 2037 has 62% of its DV01 at its own maturity (0.297 of 0.475), with the
rest spread over the earlier pillars through its coupons.

Figures: `figs/zero_forward_curve.png`, `figs/curve_snapshots.png` (2024,
2025 and 2026), `figs/key_rate_dv01.png`.

## Answers

1. **Why a flat-forward interpolation?** It is the market convention, it keeps
   forward rates piecewise constant and interpretable, and it prices each
   pillar's own cash flow exactly. Its weakness is forwards that jump at the
   pillars (12.48% to 12.89% to 13.33% above); smoother methods (splines,
   Nelson-Siegel) trade that for less exact repricing.
2. **Why is the NTN-F duration shorter than the LTN's at the same maturity?**
   Part of its value comes back as coupons before maturity. The duration of the
   2037 NTN-F is 6.1 years against 10.1 for a zero-coupon bond.
3. **What is lost by a single DV01 number?** A parallel shift hides curve risk.
   The NTN-F 2033 has 0.277 of its 0.367 DV01 at the 2033 pillar and the rest at
   earlier ones, while an LTN has all of it at a single pillar. They react
   differently to a steepening even when the total DV01 is matched.
4. **Limits.** One date; no bid-ask handling (the quotes are the Treasury's buy
   rate); a sovereign curve, not the swap curve used for derivatives; no
   accrued-interest or tax treatment.
