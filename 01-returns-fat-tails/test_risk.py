"""Unit tests for risk.py. Run with:  pytest

Each test uses data whose answer is known in advance, so a passing test
means the function is correct, not just that it runs.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import risk


@pytest.fixture
def normal_returns():
    """500,000 draws from N(0, 0.01^2): a market with no fat tails."""
    rng = np.random.default_rng(42)
    return rng.normal(loc=0.0, scale=0.01, size=500_000)


@pytest.fixture
def fat_tailed_returns():
    """500,000 draws from a Student-t with 5 degrees of freedom, scaled to
    roughly 1% daily volatility: same volatility, much heavier tails."""
    rng = np.random.default_rng(42)
    return 0.01 * rng.standard_t(df=5, size=500_000) / np.sqrt(5 / 3)


# --- log_returns ------------------------------------------------------------

def test_log_returns_values():
    prices = pd.Series([100.0, 110.0, 121.0])
    r = risk.log_returns(prices)
    assert len(r) == 2
    assert np.allclose(r.values, np.log(1.1))


def test_log_returns_add_up_over_time():
    # The property that makes log returns convenient: they sum across time.
    prices = pd.Series([100.0, 95.0, 103.0, 99.0, 120.0])
    r = risk.log_returns(prices)
    assert np.isclose(r.sum(), np.log(120.0 / 100.0))


# --- summary_stats ----------------------------------------------------------

def test_summary_stats_keys_and_basic_values():
    r = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    s = risk.summary_stats(r)
    assert set(s) == {"n", "mean", "vol", "ann_vol", "skew", "excess_kurtosis"}
    assert s["n"] == 5
    assert np.isclose(s["mean"], 0.002)
    assert np.isclose(s["vol"], np.std(r, ddof=1))
    assert np.isclose(s["ann_vol"], s["vol"] * np.sqrt(252))


def test_summary_stats_normal_sample(normal_returns):
    s = risk.summary_stats(normal_returns)
    assert abs(s["skew"]) < 0.02
    assert abs(s["excess_kurtosis"]) < 0.05


def test_summary_stats_detects_fat_tails(fat_tailed_returns):
    # Theoretical excess kurtosis of a t(5) is 6.
    s = risk.summary_stats(fat_tailed_returns)
    assert s["excess_kurtosis"] > 2


# --- jarque_bera ------------------------------------------------------------

def test_jarque_bera_matches_scipy():
    rng = np.random.default_rng(7)
    r = rng.standard_t(df=4, size=2_000)
    jb, p = risk.jarque_bera(r)
    ref = stats.jarque_bera(r)
    assert np.isclose(jb, ref.statistic)
    assert np.isclose(p, ref.pvalue)


def test_jarque_bera_does_not_reject_normal():
    rng = np.random.default_rng(1)
    _, p = risk.jarque_bera(rng.normal(size=5_000))
    assert p > 0.05


def test_jarque_bera_rejects_fat_tails(fat_tailed_returns):
    _, p = risk.jarque_bera(fat_tailed_returns[:5_000])
    assert p < 0.001


# --- historical_var ---------------------------------------------------------

def test_historical_var_known_value():
    # 101 evenly spaced returns from -5% to +5%: the 5% quantile is -4.5%.
    r = np.linspace(-0.05, 0.05, 101)
    assert np.isclose(risk.historical_var(r, alpha=0.95), 0.045)


def test_historical_var_is_a_positive_loss(normal_returns):
    assert risk.historical_var(normal_returns, alpha=0.99) > 0


def test_historical_var_increases_with_confidence(normal_returns):
    assert risk.historical_var(normal_returns, 0.99) > risk.historical_var(normal_returns, 0.95)


# --- parametric_var ---------------------------------------------------------

def test_parametric_var_formula():
    r = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    expected = -(r.mean() + r.std(ddof=1) * stats.norm.ppf(0.01))
    assert np.isclose(risk.parametric_var(r, alpha=0.99), expected)


def test_parametric_var_textbook_number(normal_returns):
    # With mu = 0 and sigma = 1%, 99% VaR is 2.326 standard deviations.
    assert np.isclose(risk.parametric_var(normal_returns, 0.99), 0.02326, atol=2e-4)


def test_both_methods_agree_when_returns_are_normal(normal_returns):
    h = risk.historical_var(normal_returns, 0.99)
    p = risk.parametric_var(normal_returns, 0.99)
    assert np.isclose(h, p, rtol=0.02)


# --- historical_es ----------------------------------------------------------

def test_historical_es_known_value():
    # Worst 5% of 101 evenly spaced returns are -5.0% ... -4.5% (6 points).
    r = np.linspace(-0.05, 0.05, 101)
    assert np.isclose(risk.historical_es(r, alpha=0.95), 0.0475)


def test_es_is_at_least_var(fat_tailed_returns):
    for alpha in (0.95, 0.99):
        assert risk.historical_es(fat_tailed_returns, alpha) >= risk.historical_var(fat_tailed_returns, alpha)


# --- the lesson of this project ---------------------------------------------

def test_normal_var_underestimates_the_far_tail(fat_tailed_returns):
    """With fat tails, the normal model understates risk at 99% but
    OVERSTATES it at 95%. Understanding why is question 3 in the README."""
    r = fat_tailed_returns
    assert risk.historical_var(r, 0.99) > risk.parametric_var(r, 0.99)
    assert risk.historical_var(r, 0.95) < risk.parametric_var(r, 0.95)
