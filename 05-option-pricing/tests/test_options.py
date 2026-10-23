"""Tests for options.py. Run with:  pytest"""

import numpy as np
import pytest

from src import options as o

S, K, T, R, SIG = 100.0, 100.0, 1.0, 0.05, 0.20


def test_textbook_value():
    # S=K=100, T=1, r=5%, sigma=20%: call 10.4506, put 5.5735 (standard textbook values)
    assert np.isclose(o.bs_price(S, K, T, R, SIG, "call"), 10.4506, atol=1e-4)
    assert np.isclose(o.bs_price(S, K, T, R, SIG, "put"), 5.5735, atol=1e-4)


@pytest.mark.parametrize("strike", [80, 100, 120])
@pytest.mark.parametrize("q", [0.0, 0.03])
def test_put_call_parity(strike, q):
    c = o.bs_price(S, strike, T, R, SIG, "call", q)
    p = o.bs_price(S, strike, T, R, SIG, "put", q)
    assert np.isclose(c - p, S * np.exp(-q * T) - strike * np.exp(-R * T))


@pytest.mark.parametrize("kind", ["call", "put"])
def test_greeks_match_finite_differences(kind):
    g = o.bs_greeks(S, K, T, R, SIG, kind)
    h = 1e-4

    def f(s=S, t=T, r=R, v=SIG):
        return o.bs_price(s, K, t, r, v, kind)

    assert np.isclose(g["delta"], (f(s=S + h) - f(s=S - h)) / (2 * h), atol=1e-6)
    assert np.isclose(g["gamma"], (f(s=S + h) - 2 * f() + f(s=S - h)) / h ** 2, atol=1e-4)
    assert np.isclose(g["vega"], (f(v=SIG + h) - f(v=SIG - h)) / (2 * h), atol=1e-5)
    assert np.isclose(g["rho"], (f(r=R + h) - f(r=R - h)) / (2 * h), atol=1e-4)
    assert np.isclose(g["theta"], -(f(t=T + h) - f(t=T - h)) / (2 * h), atol=1e-4)


def test_delta_bounds_and_call_put_relation():
    gc = o.bs_greeks(S, K, T, R, SIG, "call")
    gp = o.bs_greeks(S, K, T, R, SIG, "put")
    assert 0 < gc["delta"] < 1 and -1 < gp["delta"] < 0
    assert np.isclose(gc["delta"] - gp["delta"], 1.0)           # q = 0
    assert np.isclose(gc["gamma"], gp["gamma"]) and np.isclose(gc["vega"], gp["vega"])


@pytest.mark.parametrize("sig", [0.05, 0.2, 0.8, 2.0])
@pytest.mark.parametrize("kind", ["call", "put"])
def test_implied_vol_roundtrip(sig, kind):
    p = o.bs_price(S, 110.0, 0.5, R, sig, kind)
    assert np.isclose(o.implied_vol(p, S, 110.0, 0.5, R, kind), sig, atol=1e-6)


def test_implied_vol_rejects_arbitrage_prices():
    assert np.isnan(o.implied_vol(0.0, S, K, T, R, "call"))
    assert np.isnan(o.implied_vol(S + 1, S, K, T, R, "call"))     # above the spot


def test_monte_carlo_within_error_of_bs():
    exact = o.bs_price(S, K, T, R, SIG)
    for kw in ({"antithetic": False}, {"antithetic": True}, {"antithetic": True, "control_variate": True}):
        price, se = o.mc_price(S, K, T, R, SIG, n=200_000, seed=3, **kw)
        assert abs(price - exact) < 4 * se


def test_variance_reduction_actually_reduces_error():
    def se(**kw):
        return o.mc_price(S, K, T, R, SIG, n=100_000, seed=1, **kw)[1]

    assert se(antithetic=True) < se(antithetic=False)
    assert se(antithetic=True, control_variate=True) < se(antithetic=True)


def test_binomial_converges_to_black_scholes():
    exact = o.bs_price(S, K, T, R, SIG, "put")
    err = [abs(o.crr_price(S, K, T, R, SIG, "put", steps=n) - exact) for n in (50, 200, 800)]
    assert err[2] < err[0] and err[2] < 0.01


def test_american_put_dominates_european_and_intrinsic():
    eu = o.crr_price(S, 110.0, T, R, SIG, "put", steps=400)
    am = o.crr_price(S, 110.0, T, R, SIG, "put", steps=400, american=True)
    assert am > eu
    assert am >= 110.0 - S


def test_american_call_without_dividends_equals_european():
    eu = o.crr_price(S, K, T, R, SIG, "call", steps=400)
    am = o.crr_price(S, K, T, R, SIG, "call", steps=400, american=True)
    assert np.isclose(eu, am, atol=1e-8)
