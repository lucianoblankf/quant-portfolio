"""Tests for engine.py. Run with:  pytest"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import engine as e


@pytest.fixture
def pf():
    return e.Portfolio(equity={"A": 600.0, "B": 400.0}, fx={"USD": 200.0},
                       bond_value=500.0, bond_years=3.0, bond_yield=0.12, rate_factor="rate")


@pytest.fixture
def cov():
    names = ["A", "B", "USD", "rate"]
    vol = np.array([0.015, 0.02, 0.01, 0.0006])
    corr = np.array([[1, .6, -.3, -.2], [.6, 1, -.2, -.1], [-.3, -.2, 1, .1], [-.2, -.1, .1, 1]])
    return pd.DataFrame(np.outer(vol, vol) * corr, index=names, columns=names)


def draws(cov, n=300_000, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.multivariate_normal(np.zeros(len(cov)), cov.to_numpy(), n), columns=cov.columns)


def test_pnl_equity_and_fx_are_exact():
    p = e.Portfolio(equity={"A": 100.0}, fx={"USD": 50.0})
    s = pd.DataFrame({"A": [np.log(0.9)], "USD": [np.log(1.1)]})
    assert np.isclose(p.pnl(s)[0], -10.0 + 5.0)


def test_pnl_bond_revaluation():
    p = e.Portfolio(bond_value=1000.0, bond_years=2.0, bond_yield=0.10)
    s = pd.DataFrame({"rate": [0.01]})
    assert np.isclose(p.pnl(s)[0], 1000 * ((1.10 / 1.11) ** 2 - 1))


def test_bond_exposure_is_minus_modified_duration():
    p = e.Portfolio(bond_value=1000.0, bond_years=3.0, bond_yield=0.12)
    assert np.isclose(p.exposures()["rate"], -1000 * 3 / 1.12)


def test_var_es_known_values():
    pnl = np.linspace(-5, 5, 1001)              # losses uniform on [-5, 5]
    var, es = e.var_es(pnl, 0.95)
    assert np.isclose(var, 4.5, atol=0.01)
    assert np.isclose(es, 4.75, atol=0.02)


def test_methods_agree_on_normal_linear_portfolio(cov):
    p = e.Portfolio(equity={"A": 600.0, "B": 400.0}, fx={"USD": 200.0})
    R = draws(cov[["A", "B", "USD"]].loc[["A", "B", "USD"]])
    v_dn, es_dn = e.delta_normal(p, R.cov(), 0.99)
    v_h, es_h = e.historical(p, R, window=None, alpha=0.99)
    assert np.isclose(v_dn, v_h, rtol=0.03)
    assert np.isclose(es_dn, es_h, rtol=0.04)


def test_delta_normal_closed_form_single_asset():
    p = e.Portfolio(equity={"A": 1000.0})
    c = pd.DataFrame([[0.02 ** 2]], index=["A"], columns=["A"])
    v, es = e.delta_normal(p, c, 0.99)
    assert np.isclose(v, 1000 * 0.02 * 2.3263, rtol=1e-3)
    assert es > v


def test_component_var_adds_up_to_total(pf, cov):
    comp = e.component_var(pf, cov, 0.99)
    total, _ = e.delta_normal(pf, cov, 0.99)
    assert np.isclose(comp["component_var"].sum(), total)
    assert np.isclose(comp["share"].sum(), 1.0)


def test_var_is_homogeneous_of_degree_one(cov):
    p1 = e.Portfolio(equity={"A": 600.0, "B": 400.0})
    p2 = e.Portfolio(equity={"A": 1200.0, "B": 800.0})
    assert np.isclose(2 * e.delta_normal(p1, cov, 0.99)[0], e.delta_normal(p2, cov, 0.99)[0])


def test_diversification_reduces_var(cov):
    both = e.Portfolio(equity={"A": 500.0, "B": 500.0})
    only_a = e.Portfolio(equity={"A": 500.0})
    only_b = e.Portfolio(equity={"B": 500.0})
    v = lambda p: e.delta_normal(p, cov, 0.99)[0]
    assert v(both) < v(only_a) + v(only_b)


def test_monte_carlo_t_has_fatter_tail_than_normal_at_999(pf, cov):
    v_t, _ = e.monte_carlo_t(pf, cov, nu=4, alpha=0.999, n=400_000)
    v_n, _ = e.delta_normal(pf, cov, 0.999)
    assert v_t > v_n


def test_monte_carlo_t_matches_normal_variance(cov):
    # the t draws are scaled to the same covariance, so a moderate quantile is similar
    p = e.Portfolio(equity={"A": 600.0, "B": 400.0})
    v_t, _ = e.monte_carlo_t(p, cov, nu=30, alpha=0.95, n=400_000)
    v_n, _ = e.delta_normal(p, cov, 0.95)
    assert np.isclose(v_t, v_n, rtol=0.04)


def test_ewma_cov_weights_recent_data():
    x = pd.DataFrame({"A": [0.0] * 200 + [0.05] * 5})
    assert e.ewma_cov(x, 0.94).loc["A", "A"] > x.cov().loc["A", "A"] * 0.5
    calm = pd.DataFrame({"A": [0.05] * 5 + [0.0] * 200})
    assert e.ewma_cov(calm, 0.94).loc["A", "A"] < calm.cov().loc["A", "A"]


def test_stress_single_shock(pf):
    pnl = e.stress(pf, {"A": np.log(0.7)})
    assert np.isclose(pnl, 600 * (0.7 - 1))


def test_worst_window_finds_the_crash():
    idx = pd.date_range("2020-01-01", periods=60, freq="B")
    r = pd.DataFrame({"A": np.zeros(60)}, index=idx)
    r.iloc[30:35, 0] = -0.05
    p = e.Portfolio(equity={"A": 100.0})
    day, pnl = e.worst_window(p, r, days=5)
    assert day == idx[34]
    assert pnl < -20


def test_kupiec_perfect_and_bad():
    lr, pval = e.kupiec(10, 1000, 0.01)
    assert np.isclose(lr, 0, atol=1e-9) and pval > 0.99
    assert e.kupiec(30, 1000, 0.01)[1] < 0.001
