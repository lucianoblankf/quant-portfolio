"""Tests for volml.py. Run with:  pytest"""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

import volml as v


def fake_ohlc(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    spread = np.abs(rng.normal(0.01, 0.003, n))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({"Open": np.r_[close[0], close[:-1]], "High": close * (1 + spread),
                         "Low": close * (1 - spread), "Close": close}, index=idx)


def test_parkinson_variance_known_value():
    h, l = pd.Series([np.exp(0.02)]), pd.Series([1.0])
    assert np.isclose(v.parkinson_variance(h, l).iloc[0], 0.02 ** 2 / (4 * np.log(2)))


def test_parkinson_is_unbiased_for_brownian_motion():
    rng = np.random.default_rng(1)
    sigma, m, n = 0.02, 400, 4000
    steps = rng.normal(0, sigma / np.sqrt(m), (n, m)).cumsum(axis=1)
    path = np.exp(np.c_[np.zeros(n), steps])
    est = v.parkinson_variance(pd.Series(path.max(axis=1)), pd.Series(path.min(axis=1))).mean()
    assert np.isclose(est, sigma ** 2, rtol=0.08)          # discrete sampling biases it slightly low


def test_features_do_not_look_ahead():
    o = fake_ohlc()
    a = v.make_dataset(o)
    o2 = o.copy()
    o2.iloc[300:, :] *= 1.5                                # change the future
    b = v.make_dataset(o2)
    cols = [c for c in a if c.startswith("f_")]
    common = a.index[a.index < o.index[300]]
    pd.testing.assert_frame_equal(a.loc[common, cols], b.loc[common, cols])


def test_target_is_mean_of_next_h_days():
    o = fake_ohlc()
    d = v.make_dataset(o, h=5)
    t = 100
    rv = v.parkinson_variance(o["High"], o["Low"]).clip(lower=v.EPS)
    expected = np.log(rv.iloc[t + 1: t + 6].mean())
    assert np.isclose(d["y"].loc[o.index[t]], expected)


def test_walk_forward_recovers_linear_relation_and_has_no_leakage():
    rng = np.random.default_rng(3)
    n = 600
    x = rng.normal(size=n)
    data = pd.DataFrame({"f_x": x, "y": 2 * x + rng.normal(0, 0.1, n)})
    res = v.walk_forward(data, {"ols": LinearRegression()}, {"ols": ["f_x"]}, start=200, refit=50, h=5)
    assert v.mse_log(res["y"], res["ols"]) < 0.02
    # Changing targets after the first refit block must not change the first block's forecasts
    data2 = data.copy()
    data2.loc[250:, "y"] += 100
    res2 = v.walk_forward(data2, {"ols": LinearRegression()}, {"ols": ["f_x"]}, start=200, refit=50, h=5)
    pd.testing.assert_series_equal(res["ols"].iloc[:50], res2["ols"].iloc[:50])


def test_qlike_zero_at_truth_and_asymmetric():
    y = np.log(np.array([1.0, 2.0, 0.5]))
    assert np.isclose(v.qlike(y, y), 0)
    under = v.qlike(np.log([1.0]), np.log([0.5]))          # forecast half the truth
    over = v.qlike(np.log([1.0]), np.log([2.0]))           # forecast double the truth
    assert under > over > 0


def test_mz_r2_perfect():
    f = np.array([1.0, 2.0, 3.0, 4.0])
    assert np.isclose(v.mz_r2(2 * f + 1, f), 1.0)


def test_diebold_mariano_detects_better_model_and_not_noise():
    rng = np.random.default_rng(0)
    good = rng.chisquare(1, 2000) * 0.5
    bad = rng.chisquare(1, 2000) * 0.5 + 0.2
    stat, p = v.diebold_mariano(good, bad, h=1)
    assert stat < 0 and p < 0.001
    same_a, same_b = rng.chisquare(1, 2000), rng.chisquare(1, 2000)
    assert v.diebold_mariano(same_a, same_b, h=1)[1] > 0.01
