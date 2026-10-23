# Project 5: Option pricing

**Question:** how do the main option pricing methods compare, how well does a
delta hedge work in practice, and does the market actually price options with
the constant volatility Black-Scholes assumes?

**Short answer:** Black-Scholes, Monte Carlo and the binomial tree agree. A
delta hedge removes most of the risk but the leftover shrinks only with the
square root of the rebalancing frequency (log-log slope -0.48), and hedging
with the wrong volatility roughly doubles it. The market does not use a flat
volatility: SPY options 34 days from expiry show an implied volatility of 24% for
strikes below 95% of spot against 13% above 105%.

## What this project covers

- Black-Scholes-Merton prices and Greeks (delta, gamma, vega, theta, rho)
- Implied volatility with a bracketed root finder, and how it handles
  prices that violate no-arbitrage bounds
- Monte Carlo with antithetic variates and a control variate
- A Cox-Ross-Rubinstein binomial tree for American options
- A delta-hedging simulation
- A real volatility smile from SPY option quotes

## Files

| Path | Purpose |
|------|---------|
| `00_run_all.py` | Runs the tests, then the numbered scripts in order |
| `01_get_data.py` | Downloads the raw SPY option chain once (needs internet; skipped otherwise) |
| `02_pricing_experiments.py` | Monte Carlo variance reduction and binomial tree convergence |
| `03_delta_hedging.py` | Hedging error by rebalancing frequency and by hedge volatility |
| `04_volatility_smile.py` | Implied volatilities of SPY options with our own solver |
| `05_figures.py` | Figures in `figs/` (plotnine, 300 dpi) |
| `src/options.py` | `bs_price`, `bs_greeks`, `implied_vol`, `mc_price`, `crr_price` |
| `src/hedging.py`, `src/data.py`, `src/plots.py`, `src/reporting.py`, `src/config.py` | Hedging simulation, data, plots, console and table export, parameters and seeds |
| `tests/test_options.py` | 24 tests: textbook values, put-call parity, Greeks against finite differences, IV round trip, MC within error, tree convergence, American vs European |
| `tabs/` | Result tables as `.csv`, `.tex` and `.html` |

Open the project folder in your IDE (working directory = project root) and run
`00_run_all.py`. Parameters and seeds are in `src/config.py`. Needs: numpy, pandas,
scipy, plotnine, pyjanitor, rich, pyarrow, jinja2, yfinance, pytest.

## Results

Reference: S = K = 100, T = 1, r = 5%, sigma = 20%: call 10.4506, put 5.5735.

**1. Monte Carlo.** Standard error at one million simulations: 0.0147 plain,
0.0104 antithetic, 0.0078 antithetic plus control variate. That is 1.4 and 1.9
times lower, equal to needing about 2 and 3.5 times fewer paths for the same
precision. The gain is modest because an at-the-money call payoff is not
close to linear in the terminal price, which is what the control variate needs.
Every estimate is inside its error bars of the exact value.

**2. Binomial tree.** The error of the European call falls roughly in half each time
steps double: -0.0200 at 100 steps, -0.0040 at 500, -0.0010 at 2,000. The American
put (K = 100) is worth 6.090 against 5.573 European: an early-exercise premium
of 0.517 (9% of the price). An American call on a stock with no dividends equals the
European call (tested), since waiting is never worse.

**3. Delta hedging** (short one call, 20,000 simulated paths, drift 10%):

| Rebalances | Std of P&L | Std x sqrt(n) |
|---:|---:|---:|
| 4 | 3.15 | 6.29 |
| 12 | 1.87 | 6.48 |
| 26 | 1.28 | 6.54 |
| 52 | 0.93 | 6.69 |
| 126 | 0.60 | 6.76 |
| 252 | 0.42 | 6.74 |

The mean is close to zero, as theory says, and std times square root of n is
roughly constant: the hedging error falls like 1/sqrt(n). With daily hedging
and the wrong volatility:

| Hedge volatility (true 20%) | Mean P&L | Std |
|---:|---:|---:|
| 10% | +0.16 | 2.13 |
| 15% | +0.07 | 0.99 |
| 20% | -0.00 | 0.42 |
| 25% | -0.05 | 0.80 |
| 30% | -0.08 | 1.29 |

The dispersion is smallest at the true volatility, and it grows quickly on both
sides: a 5-point error in volatility roughly doubles the risk of the hedge.

**4. A real smile.** SPY options, expiry 34 days away, 126 out-of-the-money quotes
(bid-ask midpoints), r = 4.07% (13-week T-bill), dividend yield fixed at 1.3%:

| | Implied vol |
|---|---:|
| At the money | 14.8% |
| Average, strikes below 95% of spot | 24.4% |
| Average, strikes above 105% of spot | 13.1% |

The curve slopes down from the lowest strikes, reaches its minimum near 105% of
spot and rises a little afterwards (`figs/spy_smile.png`). The median
difference between our solver and the implied volatility reported by Yahoo is 0.008
volatility points (0.8%), probably reflecting our r and q inputs.

## Answers

1. **Why does hedging error fall as 1/sqrt(n)?** Between rebalances the
   hedge ignores gamma, leaving an error proportional to gamma times the squared
   move, of order dt; its variance sums n such terms, each of order dt squared, so the total
   variance is order 1/n.
2. **Why is the hedge with the wrong volatility worse?** The delta from the wrong
   model is the wrong share count at each moment, and the mismatch accumulates
   through the life of the option.
3. **Why does the market smile, and why the skew?** Returns have fat tails and
   fall together with volatility rises; buyers pay up for downside protection.
   Black-Scholes with a single volatility cannot reproduce that, which is why
   practitioners quote prices as implied volatilities.
4. **Limits.** Constant volatility and rate in the simulations; no transaction costs
   in the hedge; the smile uses one expiry and one date, and American-style
   exercise of SPY options is ignored (we use out-of-the-money quotes to limit it).
