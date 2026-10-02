"""Risk functions for project 1: returns, moments, normality, VaR and ES.

Conventions used throughout this module:

- Returns are daily log returns, as decimals (0.01 = 1%).
- VaR and ES are reported as POSITIVE numbers representing a loss.
  A 99% VaR of 0.03 means "we expect to lose more than 3% on 1 day in 100".
- alpha is the confidence level (0.99), so the tail probability is 1 - alpha.

log_returns is done as an example. The other five functions are yours to
write: replace each `raise NotImplementedError` with the implementation,
then run `pytest` until everything passes.
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
    # Hint: np.asarray(returns, dtype=float), then .mean(), .std(ddof=1),
    # stats.skew(...) and stats.kurtosis(...).
    raise NotImplementedError("TODO: implement summary_stats")


def jarque_bera(returns) -> tuple:
    """Jarque-Bera normality test, implemented by hand.

        JB = n/6 * (S^2 + K^2 / 4)

    where S is the skewness and K the EXCESS kurtosis. Under the null
    hypothesis of normality, JB follows a chi-squared distribution with
    2 degrees of freedom.

    Returns (statistic, p_value).
    """
    # Hint: stats.chi2.sf(x, df=2) gives P(chi2 > x), which is the p-value.
    raise NotImplementedError("TODO: implement jarque_bera")


def historical_var(returns, alpha: float = 0.99) -> float:
    """Historical-simulation VaR: the empirical (1 - alpha) quantile of
    returns, with the sign flipped so the loss is positive.
    """
    # Hint: np.quantile(r, q). Which q, and what happens to the sign?
    raise NotImplementedError("TODO: implement historical_var")


def parametric_var(returns, alpha: float = 0.99) -> float:
    """Parametric (normal) VaR: assume returns ~ N(mu, sigma^2).

        VaR = -(mu + sigma * z)     with z = Phi^{-1}(1 - alpha)

    Use the sample mean and the sample standard deviation (ddof=1).
    """
    # Hint: stats.norm.ppf(p) is the inverse normal CDF. ppf(0.01) = -2.326.
    raise NotImplementedError("TODO: implement parametric_var")


def historical_es(returns, alpha: float = 0.99) -> float:
    """Historical Expected Shortfall: the average loss on the days when the
    return is at or below the (1 - alpha) quantile. Positive number.
    """
    # Hint: find the cutoff quantile first, then average the returns at or below it.
    raise NotImplementedError("TODO: implement historical_es")
