"""Option pricing from scratch: Black-Scholes, Greeks, implied volatility,
Monte Carlo (with variance reduction) and a Cox-Ross-Rubinstein binomial tree.

Notation: S spot, K strike, T years to expiry, r continuously compounded risk-free
rate, q continuous dividend yield, sigma annual volatility, kind "call" or "put".
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma, q=0.0):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return d1, d1 - sigma * np.sqrt(T)


def bs_price(S, K, T, r, sigma, kind="call", q=0.0):
    """Black-Scholes-Merton price of a European option."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    if kind == "call":
        return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    if kind == "put":
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    raise ValueError("kind must be 'call' or 'put'")


def bs_greeks(S, K, T, r, sigma, kind="call", q=0.0) -> dict:
    """Delta, gamma, vega (per 1.00 of volatility), theta (per year), rho (per 1.00 of rate)."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    pdf = norm.pdf(d1)
    eq, er = np.exp(-q * T), np.exp(-r * T)
    gamma = eq * pdf / (S * sigma * np.sqrt(T))
    vega = S * eq * pdf * np.sqrt(T)
    if kind == "call":
        delta = eq * norm.cdf(d1)
        theta = (-S * eq * pdf * sigma / (2 * np.sqrt(T)) - r * K * er * norm.cdf(d2) + q * S * eq * norm.cdf(d1))
        rho = K * T * er * norm.cdf(d2)
    else:
        delta = -eq * norm.cdf(-d1)
        theta = (-S * eq * pdf * sigma / (2 * np.sqrt(T)) + r * K * er * norm.cdf(-d2) - q * S * eq * norm.cdf(-d1))
        rho = -K * T * er * norm.cdf(-d2)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


def implied_vol(price, S, K, T, r, kind="call", q=0.0, lo=1e-4, hi=5.0):
    """Volatility that makes the Black-Scholes price equal `price`. Returns NaN if the
    price violates the no-arbitrage bounds (no solution)."""
    sign = 1 if kind == "call" else -1
    intrinsic = max(0.0, sign * (S * np.exp(-q * T) - K * np.exp(-r * T)))
    if not np.isfinite(price) or price <= intrinsic + 1e-12:
        return np.nan

    def f(s):
        return bs_price(S, K, T, r, s, kind, q) - price

    if f(lo) * f(hi) > 0:
        return np.nan
    return brentq(f, lo, hi, xtol=1e-12)


def mc_price(S, K, T, r, sigma, kind="call", q=0.0, n=100_000, antithetic=True,
             control_variate=False, seed=0):
    """Monte Carlo price of a European option under geometric Brownian motion.

    Returns (price, standard_error). Variance reduction:
      antithetic       -- pair every draw z with -z
      control_variate  -- subtract beta * (c - E[c]) where c is the discounted terminal
                          price, whose expectation S exp(-qT) is known exactly
    """
    rng = np.random.default_rng(seed)
    m = n // 2 if antithetic else n
    z = rng.standard_normal(m)
    if antithetic:
        z = np.concatenate([z, -z])
    ST = S * np.exp((r - q - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * z)
    payoff = np.maximum(ST - K, 0.0) if kind == "call" else np.maximum(K - ST, 0.0)
    disc = np.exp(-r * T)
    x = disc * payoff
    if control_variate:
        c = disc * ST
        beta = np.cov(x, c)[0, 1] / np.var(c, ddof=1)
        x = x - beta * (c - S * np.exp(-q * T))
    if antithetic:
        x = 0.5 * (x[:m] + x[m:])        # each pair is one independent observation
    return float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x)))


def crr_price(S, K, T, r, sigma, kind="call", q=0.0, steps=500, american=False):
    """Cox-Ross-Rubinstein binomial tree (European or American)."""
    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    p = (np.exp((r - q) * dt) - d) / (u - d)
    disc = np.exp(-r * dt)
    j = np.arange(steps + 1)
    ST = S * u ** (steps - j) * d ** j
    V = np.maximum(ST - K, 0.0) if kind == "call" else np.maximum(K - ST, 0.0)
    for i in range(steps - 1, -1, -1):
        V = disc * (p * V[:-1] + (1 - p) * V[1:])
        if american:
            Si = S * u ** (i - np.arange(i + 1)) * d ** np.arange(i + 1)
            ex = np.maximum(Si - K, 0.0) if kind == "call" else np.maximum(K - Si, 0.0)
            V = np.maximum(V, ex)
    return float(V[0])
