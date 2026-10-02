# Quant Portfolio

Small, self-contained projects in quantitative finance and market risk, built
with Brazilian market data. Each project implements the method from scratch,
tests it, and applies it to real data, in Python with an R mirror.

By Luciano Blank Fonseca.

## Projects

| # | Project | Topics | Status |
|---|---------|--------|--------|
| 1 | [Returns and fat tails](01-returns-fat-tails/) | Log returns, moments, Jarque-Bera, historical and parametric VaR, Expected Shortfall | In progress |
| 2 | Volatility and VaR backtesting | GARCH, daily VaR, Kupiec test | Planned |
| 3 | The DI curve | Bootstrapping from DI1 futures, flat-forward interpolation, LTN/NTN-F pricing, DV01 | Planned |
| 4 | PCA of the yield curve | Level, slope, curvature, stress scenarios | Planned |
| 5 | Option pricing | Black-Scholes, Greeks, Monte Carlo | Planned |
| 6 | Mini risk engine | Risk-factor mapping, VaR, ES, stress testing | Planned |

## Setup

```bash
conda create -n quant python=3.12
conda activate quant
pip install -r requirements.txt
```

## Running a project

```bash
cd 01-returns-fat-tails
pytest            # unit tests for the risk functions
python analysis.py
```
