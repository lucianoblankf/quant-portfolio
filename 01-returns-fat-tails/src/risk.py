"""Risk functions for project 1: returns, moments, normality, VaR and ES.

Conventions used throughout this module:

- Returns are daily log returns, as decimals (0.01 = 1%).
- VaR and ES are reported as POSITIVE numbers representing a loss.
  A 99% VaR of 0.03 means "we expect to lose more than 3% on 1 day in 100".
- alpha is the confidence level (0.99), so the tail probability is 1 - alpha.

Everything is implemented from scratch on top of numpy/scipy primitives and
checked against known answers in test_risk.py.
"""

import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252


def log_returns(prices: pd.Series) -> pd.Series:
    """Daily log returns: r_t = ln(P_t / P_{t-1}).

    The first observation has no previous price, so it is dropped.
    """
    return np.log(prices / prices.shift(1)).dropna()


def summary_stats(returns) -> dict:
    """Descriptive statistics of a return series.

    Returns a dict with keys:
        n               number of observations
        mean            daily mean
        vol             daily standard deviation (sample, ddof=1)
        ann_vol         annualised volatility = vol * sqrt(252)
        skew            skewness (scipy.stats.skew, default settings)
        excess_kurtosis kurtosis minus 3 (scipy.stats.kurtosis, default settings)
    """
    r = np.asarray(returns, dtype=float)
    vol = r.std(ddof=1)
    return {
        "n": int(r.size),
        "mean": float(r.mean()),
        "vol": float(vol),
        "ann_vol": float(vol * np.sqrt(TRADING_DAYS)),
        "skew": float(stats.skew(r)),
        "excess_kurtosis": float(stats.kurtosis(r)),
    }


def jarque_bera(returns) -> tuple:
    """Jarque-Bera normality test, implemented by hand.

        JB = n/6 * (S^2 + K^2 / 4)

    where S is the skewness and K the EXCESS kurtosis. Under the null
    hypothesis of normality, JB follows a chi-squared distribution with
    2 degrees of freedom.

    Returns (statistic, p_value).
    """
    r = np.asarray(returns, dtype=float)
    s = stats.skew(r)
    k = stats.kurtosis(r)
    jb = r.size / 6 * (s**2 + k**2 / 4)
    return float(jb), float(stats.chi2.sf(jb, df=2))


def historical_var(returns, alpha: float = 0.99) -> float:
    """Historical-simulation VaR: the empirical (1 - alpha) quantile of
    returns, with the sign flipped so the loss is positive.
    """
    r = np.asarray(returns, dtype=float)
    return float(-np.quantile(r, 1 - alpha))


def parametric_var(returns, alpha: float = 0.99) -> float:
    """Parametric (normal) VaR: assume returns ~ N(mu, sigma^2).

        VaR = -(mu + sigma * z)     with z = Phi^{-1}(1 - alpha)

    Use the sample mean and the sample standard deviation (ddof=1).
    """
    r = np.asarray(returns, dtype=float)
    z = stats.norm.ppf(1 - alpha)
    return float(-(r.mean() + r.std(ddof=1) * z))


def historical_es(returns, alpha: float = 0.99) -> float:
    """Historical Expected Shortfall: the average loss on the days when the
    return is at or below the (1 - alpha) quantile. Positive number.
    """
    r = np.asarray(returns, dtype=float)
    cutoff = np.quantile(r, 1 - alpha)
    return float(-r[r <= cutoff].mean())
