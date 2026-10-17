"""Volatility forecasting with econometric and machine-learning models.

Target: the log of the average Parkinson (high-low) variance over the next `h` days.
Features use only information up to day t. Models are re-fitted on an expanding window
and evaluated strictly out of sample (walk-forward).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone

EPS = 1e-10


def parkinson_variance(high: pd.Series, low: pd.Series) -> pd.Series:
    """Daily variance estimate from the high-low range: (ln H/L)^2 / (4 ln 2)."""
    return np.log(high / low) ** 2 / (4 * np.log(2))


def make_dataset(ohlc: pd.DataFrame, fx_close: pd.Series | None = None, h: int = 5) -> pd.DataFrame:
    """Build features (columns f_*) and the target `y` (log mean variance over t+1..t+h).

    ohlc needs columns Open, High, Low, Close. `fx_close` is an optional second asset
    used for a spillover feature.
    """
    d = pd.DataFrame(index=ohlc.index)
    ret = np.log(ohlc["Close"]).diff()
    rv = parkinson_variance(ohlc["High"], ohlc["Low"]).clip(lower=EPS)
    d["rv"] = rv
    d["f_logrv_1"] = np.log(rv)
    d["f_logrv_5"] = np.log(rv.rolling(5).mean())
    d["f_logrv_22"] = np.log(rv.rolling(22).mean())
    d["f_logrv_66"] = np.log(rv.rolling(66).mean())
    d["f_absret"] = ret.abs()
    d["f_ret"] = ret
    d["f_neg_ret_5"] = ret.clip(upper=0).rolling(5).sum()          # leverage effect
    d["f_gap"] = np.log(ohlc["Open"] / ohlc["Close"].shift(1)).abs()
    if fx_close is not None:
        fx_ret = np.log(fx_close).diff().reindex(d.index)
        d["f_fx_absret_5"] = fx_ret.abs().rolling(5).mean()
    fwd = rv[::-1].rolling(h).mean()[::-1].shift(-1)               # mean of rv over t+1..t+h
    d["y"] = np.log(fwd)
    return d.dropna(subset=[c for c in d if c.startswith("f_")]).copy()


# --------------------------------------------------------------------------
# Benchmarks that are not scikit-learn estimators
# --------------------------------------------------------------------------

def ewma_forecast(rv: pd.Series, lam: float = 0.94, h: int = 5) -> pd.Series:
    """EWMA of daily variance, used as the forecast of the average variance over the next
    h days (log). Uses data up to t."""
    s = rv.ewm(alpha=1 - lam, adjust=False).mean()
    return np.log(s)


# --------------------------------------------------------------------------
# Walk-forward evaluation
# --------------------------------------------------------------------------

def walk_forward(data: pd.DataFrame, models: dict, features: dict, start: int = 750,
                 refit: int = 63, h: int = 5) -> pd.DataFrame:
    """Out-of-sample log-variance forecasts.

    models   {name: sklearn estimator}
    features {name: list of feature columns}
    At each refit date t0 the model is trained on rows whose target is fully known by t0
    (the last h rows are excluded, so no overlap with the future), then predicts the
    next `refit` rows.
    """
    n = len(data)
    out = {name: np.full(n, np.nan) for name in models}
    for t0 in range(start, n, refit):
        train = data.iloc[: t0 - h].dropna(subset=["y"])
        test_idx = slice(t0, min(t0 + refit, n))
        for name, est in models.items():
            cols = features[name]
            m = clone(est).fit(train[cols], train["y"])
            out[name][test_idx] = m.predict(data.iloc[test_idx][cols])
    res = pd.DataFrame(out, index=data.index)
    res["y"] = data["y"]
    return res.iloc[start:].dropna(subset=["y"])


# --------------------------------------------------------------------------
# Loss functions and tests
# --------------------------------------------------------------------------

def mse_log(y, f):
    return float(np.mean((np.asarray(y) - np.asarray(f)) ** 2))


def qlike(y_log, f_log):
    """QLIKE loss on variances: sigma2/f - ln(sigma2/f) - 1, with log inputs. Robust loss
    for volatility forecasting; penalises under-prediction more than over-prediction."""
    r = np.exp(np.asarray(y_log) - np.asarray(f_log))
    return float(np.mean(r - np.log(r) - 1))


def mz_r2(y, f):
    """R^2 of the Mincer-Zarnowitz regression y = a + b f."""
    y, f = np.asarray(y), np.asarray(f)
    return float(stats.linregress(f, y).rvalue ** 2)


def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray, h: int = 5):
    """DM test of equal predictive accuracy on loss differentials, with a Newey-West
    variance using h-1 lags (forecast errors overlap by construction). Harvey-Leybourne-
    Newbold small-sample correction. Returns (statistic, two-sided p-value); a negative
    statistic means model A has the lower loss."""
    d = np.asarray(loss_a) - np.asarray(loss_b)
    n = len(d)
    dbar = d.mean()
    lags = max(h - 1, 0)
    gamma = [np.mean((d[k:] - dbar) * (d[:n - k] - dbar)) for k in range(lags + 1)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    dm = dbar / np.sqrt(var)
    dm *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(dm), float(2 * stats.t.sf(abs(dm), n - 1))
