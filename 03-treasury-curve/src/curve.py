"""Zero curve bootstrapping and fixed-income risk for Brazilian pre-fixed bonds.

Conventions (the Brazilian market standard):

- Rates are annual, compounded, on a business-day basis: DF(t) = (1 + y)^(-du/252),
  where du is the number of business days (ANBIMA holiday calendar) between the
  valuation date and the cash flow.
- LTN (Tesouro Prefixado): one cash flow of 1000 at maturity.
- NTN-F (Tesouro Prefixado com Juros Semestrais): 1000 face, coupons of
  1000 * (1.10^0.5 - 1) = 48.8088 on every 1 January and 1 July, plus the face
  at maturity.
- Between pillars the curve is flat-forward: ln DF is linear in du, so the
  forward rate is constant between two consecutive pillars.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from dateutil.easter import easter
from scipy.optimize import brentq

FACE = 1000.0
COUPON = FACE * (1.10 ** 0.5 - 1.0)  # 48.8088
BASIS = 252


# --------------------------------------------------------------------------
# Calendar
# --------------------------------------------------------------------------

def br_holidays(years) -> list:
    """Brazilian national holidays that close the financial market (ANBIMA list).

    Fixed dates, plus Carnival Monday and Tuesday, Good Friday and Corpus Christi
    (all derived from Easter), plus Consciencia Negra (20 Nov, national from 2024).
    """
    out = []
    for y in years:
        e = easter(y)
        fixed = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
        if y >= 2024:
            fixed.append((11, 20))
        out += [date(y, m, d) for m, d in fixed]
        out += [e - timedelta(days=48), e - timedelta(days=47),   # Carnival
                e - timedelta(days=2),                            # Good Friday
                e + timedelta(days=60)]                           # Corpus Christi
    return sorted(out)


def business_days(start: date, end: date) -> int:
    """Number of business days in [start, end): the du of the Brazilian convention."""
    hol = np.array(br_holidays(range(start.year, end.year + 1)), dtype="datetime64[D]")
    return int(np.busday_count(np.datetime64(start), np.datetime64(end), holidays=hol))


def next_business_day(d: date) -> date:
    """First business day strictly after `d`."""
    d = d + timedelta(days=1)
    hol = set(br_holidays([d.year, d.year + 1]))
    while d.weekday() >= 5 or d in hol:
        d += timedelta(days=1)
    return d


# --------------------------------------------------------------------------
# Cash flows and pricing
# --------------------------------------------------------------------------

def coupon_dates(valuation: date, maturity: date) -> list:
    """Coupon dates (1 Jan / 1 Jul) strictly after the valuation date, up to maturity."""
    out = []
    for y in range(valuation.year, maturity.year + 1):
        for m in (1, 7):
            d = date(y, m, 1)
            if valuation < d <= maturity:
                out.append(d)
    return out


def cash_flows(kind: str, valuation: date, maturity: date) -> list:
    """List of (date, amount) for an LTN or an NTN-F."""
    if kind == "LTN":
        return [(maturity, FACE)]
    if kind == "NTN-F":
        cfs = [(d, COUPON) for d in coupon_dates(valuation, maturity)]
        cfs[-1] = (cfs[-1][0], cfs[-1][1] + FACE)
        return cfs
    raise ValueError(f"unknown bond type {kind!r}")


@dataclass
class Curve:
    """Zero curve defined by pillars (du, annual rate), flat-forward in between."""

    valuation: date
    du: np.ndarray          # business days of the pillars, increasing
    rate: np.ndarray        # annual zero rates at the pillars

    def log_df(self, du) -> np.ndarray:
        """ln DF at the given du. Flat-forward inside the pillars; before the first
        pillar the first forward is extended back to du = 0; beyond the last pillar
        the last forward is extended."""
        x = np.concatenate([[0.0], self.du])
        y = np.concatenate([[0.0], -self.du / BASIS * np.log1p(self.rate)])
        du = np.asarray(du, dtype=float)
        inside = np.interp(du, x, y)
        slope_last = (y[-1] - y[-2]) / (x[-1] - x[-2])
        return np.where(du > x[-1], y[-1] + slope_last * (du - x[-1]), inside)

    def df(self, du) -> np.ndarray:
        return np.exp(self.log_df(du))

    def zero(self, du) -> np.ndarray:
        du = np.asarray(du, dtype=float)
        return np.exp(-self.log_df(du) * BASIS / du) - 1.0

    def forward(self, du_a: float, du_b: float) -> float:
        """Forward rate between two business-day points, annual, 252 basis."""
        lf = self.log_df(np.array([du_a, du_b]))
        return float(np.exp((lf[0] - lf[1]) * BASIS / (du_b - du_a)) - 1.0)

    def bumped(self, bp: float, pillar: int | None = None) -> "Curve":
        """Copy with one pillar (or all pillars) shifted by `bp` basis points."""
        r = self.rate.copy()
        if pillar is None:
            r += bp / 1e4
        else:
            r[pillar] += bp / 1e4
        return Curve(self.valuation, self.du, r)


def price(curve: Curve, kind: str, maturity: date) -> float:
    """Present value of a bond on the curve, per 1000 of face."""
    cfs = cash_flows(kind, curve.valuation, maturity)
    du = np.array([business_days(curve.valuation, d) for d, _ in cfs], dtype=float)
    amt = np.array([a for _, a in cfs])
    return float(np.sum(amt * curve.df(du)))


# --------------------------------------------------------------------------
# Bootstrapping
# --------------------------------------------------------------------------

def bootstrap(valuation: date, instruments: list) -> Curve:
    """Bootstrap a zero curve from LTN and NTN-F prices.

    `instruments` is a list of (kind, maturity, pu). They are processed in order of
    maturity. For an LTN the pillar follows directly from the price. For an NTN-F the
    coupons before maturity are discounted on the curve built so far (extended with the
    candidate pillar), and the zero rate at maturity is the root of
    PV(rate) - PU = 0. If an LTN and an NTN-F share a maturity, the LTN defines the
    pillar and the NTN-F is left as a cross-check.
    """
    items = sorted(instruments, key=lambda i: (i[1], 0 if i[0] == "LTN" else 1))
    du_list, r_list, seen = [], [], set()
    for kind, mat, pu in items:
        if mat in seen:
            continue
        seen.add(mat)
        du = business_days(valuation, mat)
        if kind == "LTN":
            rate = (FACE / pu) ** (BASIS / du) - 1.0
        else:
            def gap(r):
                c = Curve(valuation, np.array(du_list + [du], float), np.array(r_list + [r]))
                return price(c, "NTN-F", mat) - pu
            rate = brentq(gap, -0.5, 1.5, xtol=1e-14)
        du_list.append(du)
        r_list.append(rate)
    return Curve(valuation, np.array(du_list, float), np.array(r_list))


# --------------------------------------------------------------------------
# Risk
# --------------------------------------------------------------------------

def dv01(curve: Curve, kind: str, maturity: date, bp: float = 1.0) -> float:
    """Price change for a one-basis-point parallel fall in all zero rates (positive for
    a long position), per 1000 of face. Central difference."""
    up = price(curve.bumped(+bp), kind, maturity)
    dn = price(curve.bumped(-bp), kind, maturity)
    return (dn - up) / 2.0


def key_rate_dv01(curve: Curve, kind: str, maturity: date, bp: float = 1.0) -> np.ndarray:
    """DV01 with respect to each pillar separately. Their sum is the parallel DV01."""
    out = []
    for i in range(len(curve.du)):
        up = price(curve.bumped(+bp, i), kind, maturity)
        dn = price(curve.bumped(-bp, i), kind, maturity)
        out.append((dn - up) / 2.0)
    return np.array(out)


def macaulay_duration(curve: Curve, kind: str, maturity: date) -> float:
    """Duration in years (business-day basis): PV-weighted average time of the cash flows."""
    cfs = cash_flows(kind, curve.valuation, maturity)
    du = np.array([business_days(curve.valuation, d) for d, _ in cfs], dtype=float)
    pv = np.array([a for _, a in cfs]) * curve.df(du)
    return float(np.sum(pv * du / BASIS) / pv.sum())
