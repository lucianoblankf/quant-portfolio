"""A small market-risk engine: P&L vectors, VaR / ES by four methods, component VaR,
stress tests and a VaR backtest.

Conventions
-----------
- A *scenario* is a vector of risk-factor moves. Factors here are daily log returns
  (equities, FX) and daily changes of a zero-coupon yield (in decimals, 0.0001 = 1 bp).
- `Portfolio.pnl(scenarios)` revalues the portfolio under every scenario and returns the
  profit and loss in currency units. Equities and FX are linear; the bond is revalued
  exactly (so its convexity is included).
- VaR and ES are POSITIVE numbers: the loss that is exceeded with probability 1 - alpha,
  and the average loss beyond it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class Portfolio:
    """Positions in currency units.

    equity: {factor_name: market value}; return factor is a log return.
    fx:     {factor_name: market value in local currency of the foreign exposure}.
    bond:   market value of a zero-coupon bond and its maturity in years, exposed to the
            yield factor `rate_factor` (zero rate, annual compounding).
    """

    equity: dict = field(default_factory=dict)
    fx: dict = field(default_factory=dict)
    bond_value: float = 0.0
    bond_years: float = 0.0
    bond_yield: float = 0.0
    rate_factor: str = "rate"

    @property
    def factors(self) -> list:
        f = list(self.equity) + list(self.fx)
        if self.bond_value:
            f.append(self.rate_factor)
        return f

    @property
    def value(self) -> float:
        return sum(self.equity.values()) + sum(self.fx.values()) + self.bond_value

    def pnl(self, scen: pd.DataFrame) -> np.ndarray:
        """P&L under each row of `scen` (columns = factors)."""
        out = np.zeros(len(scen))
        for name, mv in {**self.equity, **self.fx}.items():
            out += mv * np.expm1(scen[name].to_numpy())
        if self.bond_value:
            y1 = self.bond_yield + scen[self.rate_factor].to_numpy()
            ratio = ((1 + self.bond_yield) / (1 + y1)) ** self.bond_years
            out += self.bond_value * (ratio - 1)
        return out

    def exposures(self) -> pd.Series:
        """Linear sensitivities (currency per unit factor move) at the current point."""
        e = {**self.equity, **self.fx}
        if self.bond_value:
            e[self.rate_factor] = -self.bond_value * self.bond_years / (1 + self.bond_yield)
        return pd.Series(e)[self.factors]


# --------------------------------------------------------------------------
# VaR and ES from a P&L vector
# --------------------------------------------------------------------------

def var_es(pnl: np.ndarray, alpha: float = 0.99):
    """Empirical VaR and ES of a P&L sample (positive loss numbers)."""
    loss = -np.asarray(pnl)
    var = np.quantile(loss, alpha)
    es = loss[loss >= var].mean()
    return float(var), float(es)


def historical(pf: Portfolio, returns: pd.DataFrame, window: int | None = 500, alpha=0.99):
    scen = returns[pf.factors].tail(window) if window else returns[pf.factors]
    return var_es(pf.pnl(scen), alpha)


def ewma_cov(returns: pd.DataFrame, lam: float = 0.94) -> pd.DataFrame:
    """RiskMetrics exponentially weighted covariance (zero mean)."""
    x = returns.to_numpy()
    w = lam ** np.arange(len(x))[::-1]
    w = w / w.sum()
    return pd.DataFrame((x * w[:, None]).T @ x, index=returns.columns, columns=returns.columns)


def delta_normal(pf: Portfolio, cov: pd.DataFrame, alpha=0.99):
    """Parametric VaR/ES with a linear portfolio and normal factors (zero mean)."""
    e = pf.exposures().to_numpy()
    sigma = float(np.sqrt(e @ cov.loc[pf.factors, pf.factors].to_numpy() @ e))
    z = stats.norm.ppf(alpha)
    return sigma * z, sigma * stats.norm.pdf(z) / (1 - alpha)


def component_var(pf: Portfolio, cov: pd.DataFrame, alpha=0.99) -> pd.DataFrame:
    """Euler allocation of the delta-normal VaR: component_i = e_i * (Cov e)_i / sigma * z.
    The components add up exactly to the total."""
    e = pf.exposures()
    C = cov.loc[pf.factors, pf.factors].to_numpy()
    sigma = np.sqrt(e.to_numpy() @ C @ e.to_numpy())
    z = stats.norm.ppf(alpha)
    marginal = (C @ e.to_numpy()) / sigma * z
    comp = e.to_numpy() * marginal
    return pd.DataFrame({"exposure": e, "marginal_var": marginal, "component_var": comp,
                         "share": comp / comp.sum()})


def monte_carlo_t(pf: Portfolio, cov: pd.DataFrame, nu: float = 5, n: int = 200_000, alpha=0.99, seed=0):
    """Full-revaluation Monte Carlo with multivariate Student-t factors, scaled so the
    covariance equals `cov`. Fat tails, unlike delta-normal."""
    rng = np.random.default_rng(seed)
    C = cov.loc[pf.factors, pf.factors].to_numpy()
    L = np.linalg.cholesky(C)
    z = rng.standard_normal((n, len(pf.factors))) @ L.T
    scale = np.sqrt((nu - 2) / rng.chisquare(nu, n))[:, None]
    scen = pd.DataFrame(z * scale, columns=pf.factors)
    return var_es(pf.pnl(scen), alpha)


# --------------------------------------------------------------------------
# Stress testing
# --------------------------------------------------------------------------

def stress(pf: Portfolio, shocks: dict) -> float:
    """P&L of one scenario given as {factor: move}; missing factors are not moved."""
    row = pd.DataFrame([{f: shocks.get(f, 0.0) for f in pf.factors}])
    return float(pf.pnl(row)[0])


def worst_window(pf: Portfolio, returns: pd.DataFrame, days: int = 5):
    """Historical stress: the worst `days`-day cumulative P&L (factor moves summed)."""
    roll = returns[pf.factors].rolling(days).sum().dropna()
    pnl = pd.Series(pf.pnl(roll), index=roll.index)
    return pnl.idxmin(), float(pnl.min())


# --------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------

def rolling_var(pf: Portfolio, returns: pd.DataFrame, method: str, alpha=0.99, window=500, lam=0.94):
    """One-day-ahead VaR for each date, from data strictly before it. Methods:
    'hist', 'normal' (rolling covariance), 'ewma'."""
    R = returns[pf.factors]
    pnl_all = pf.pnl(R)
    e = pf.exposures().to_numpy()
    z = stats.norm.ppf(alpha)
    out = []
    for t in range(window, len(R)):
        past = R.iloc[t - window:t]
        if method == "hist":
            out.append(-np.quantile(pf.pnl(past), 1 - alpha))
        elif method == "normal":
            out.append(z * np.sqrt(e @ past.cov().to_numpy() @ e))
        elif method == "ewma":
            out.append(z * np.sqrt(e @ ewma_cov(past, lam).to_numpy() @ e))
        else:
            raise ValueError(method)
    idx = R.index[window:]
    return pd.Series(out, index=idx), pd.Series(pnl_all[window:], index=idx)


def kupiec(breaches: int, n: int, p: float):
    """Kupiec proportion-of-failures LR test: (LR, p-value)."""
    x, phat = breaches, breaches / n
    ll0 = (n - x) * np.log(1 - p) + x * np.log(p)
    ll1 = (n - x) * np.log(1 - phat) + (x * np.log(phat) if x > 0 else 0.0)
    lr = -2 * (ll0 - ll1)
    return float(lr), float(stats.chi2.sf(lr, 1))
