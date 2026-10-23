"""Tests for curve.py. Run with:  pytest"""

from datetime import date

import numpy as np
import pytest

from src import curve as c

VAL = date(2026, 10, 16)


def flat_curve(rate=0.12, val=VAL, maturities=(date(2027, 1, 1), date(2030, 1, 1), date(2037, 1, 1))):
    du = np.array([c.business_days(val, m) for m in maturities], float)
    return c.Curve(val, du, np.full(len(du), rate))


# --- calendar -------------------------------------------------------------

def test_holidays_2026_movable_dates():
    h = set(c.br_holidays([2026]))
    assert date(2026, 2, 16) in h and date(2026, 2, 17) in h      # Carnival
    assert date(2026, 4, 3) in h                                  # Good Friday
    assert date(2026, 6, 4) in h                                  # Corpus Christi


def test_business_days_simple_week():
    assert c.business_days(date(2026, 10, 5), date(2026, 10, 12)) == 5   # Mon..Fri, end excluded


def test_business_days_skips_holiday():
    assert c.business_days(date(2026, 4, 1), date(2026, 4, 8)) == 4      # Good Friday off


def test_next_business_day_over_weekend():
    assert c.next_business_day(date(2026, 10, 16)) == date(2026, 10, 19)  # Friday -> Monday


# --- cash flows -----------------------------------------------------------

def test_ntnf_cash_flows():
    cfs = c.cash_flows("NTN-F", date(2026, 10, 16), date(2028, 1, 1))
    assert [d for d, _ in cfs] == [date(2027, 1, 1), date(2027, 7, 1), date(2028, 1, 1)]
    assert np.isclose(cfs[0][1], 48.8088, atol=1e-3)
    assert np.isclose(cfs[-1][1], 1000 + 48.8088, atol=1e-3)


# --- curve ---------------------------------------------------------------

def test_flat_curve_gives_flat_zero_and_closed_form_ltn():
    cv = flat_curve(0.12)
    mat = date(2030, 1, 1)
    du = c.business_days(VAL, mat)
    assert np.isclose(c.price(cv, "LTN", mat), 1000 / 1.12 ** (du / 252))
    assert np.allclose(cv.zero(np.array([100.0, 700.0, 2000.0])), 0.12)


def test_flat_forward_between_pillars():
    cv = c.Curve(VAL, np.array([252.0, 504.0]), np.array([0.10, 0.12]))
    f = cv.forward(252, 504)
    assert np.isclose((1.12 ** 2) / 1.10, 1 + f)                  # exact forward between pillars
    assert np.isclose(cv.forward(300, 400), f)                    # constant inside the segment


def test_discount_factor_decreasing():
    cv = c.Curve(VAL, np.array([100.0, 500.0, 1500.0]), np.array([0.13, 0.125, 0.12]))
    x = np.linspace(1, 2500, 200)
    assert np.all(np.diff(cv.df(x)) < 0)


# --- bootstrapping -----------------------------------------------------------

def make_market(cv):
    """Prices implied by a known curve, to test that bootstrapping recovers it."""
    ltns = [("LTN", date(y, 1, 1)) for y in (2027, 2028, 2029, 2031)]
    ntnfs = [("NTN-F", date(y, 1, 1)) for y in (2033, 2035)]
    return [(k, m, c.price(cv, k, m)) for k, m in ltns + ntnfs]


def test_bootstrap_reprices_inputs():
    truth_mats = [date(2027, 1, 1), date(2028, 1, 1), date(2029, 1, 1), date(2031, 1, 1),
                  date(2033, 1, 1), date(2035, 1, 1)]
    du = np.array([c.business_days(VAL, m) for m in truth_mats], float)
    truth = c.Curve(VAL, du, np.array([0.135, 0.128, 0.125, 0.127, 0.129, 0.130]))
    market = make_market(truth)
    built = c.bootstrap(VAL, market)
    for k, m, pu in market:
        assert abs(c.price(built, k, m) - pu) < 1e-6


def test_bootstrap_recovers_pillars_on_ltn_and_ntnf():
    truth_mats = [date(2027, 1, 1), date(2028, 1, 1), date(2029, 1, 1), date(2031, 1, 1),
                  date(2033, 1, 1), date(2035, 1, 1)]
    du = np.array([c.business_days(VAL, m) for m in truth_mats], float)
    rates = np.array([0.135, 0.128, 0.125, 0.127, 0.129, 0.130])
    built = c.bootstrap(VAL, make_market(c.Curve(VAL, du, rates)))
    assert np.allclose(built.rate, rates, atol=1e-6)


# --- risk ----------------------------------------------------------------------

def test_dv01_positive_and_matches_duration_approx():
    cv = flat_curve(0.12)
    mat = date(2030, 1, 1)
    p = c.price(cv, "LTN", mat)
    mac = c.macaulay_duration(cv, "LTN", mat)
    approx = p * mac / 1.12 * 1e-4                                # modified duration * P * 1bp
    assert c.dv01(cv, "LTN", mat) > 0
    assert np.isclose(c.dv01(cv, "LTN", mat), approx, rtol=0.01)


def test_key_rate_dv01_sums_to_parallel():
    cv = c.Curve(VAL, np.array([53.0, 304.0, 552.0, 1053.0, 1305.0]),
                 np.array([0.1337, 0.1277, 0.1264, 0.1276, 0.1287]))
    mat = date(2031, 1, 1)
    krd = c.key_rate_dv01(cv, "NTN-F", mat)
    assert np.isclose(krd.sum(), c.dv01(cv, "NTN-F", mat), rtol=1e-3)


def test_ntnf_duration_shorter_than_ltn_same_maturity():
    cv = flat_curve(0.12)
    mat = date(2037, 1, 1)
    assert c.macaulay_duration(cv, "NTN-F", mat) < c.macaulay_duration(cv, "LTN", mat)
