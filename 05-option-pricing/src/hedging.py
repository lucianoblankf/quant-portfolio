"""Delta-hedging simulation."""

import numpy as np

from src import config
from src import options as o


def delta_hedge(
    n_rebal: int,
    sigma_hedge: float,
    paths: int = config.HEDGE_PATHS,
    mu: float = config.HEDGE_DRIFT,
    seed: int = config.SEED_HEDGING,
) -> np.ndarray:
    """P&L at expiry of selling one call and delta-hedging at `n_rebal` equally spaced dates.

    The delta is computed with `sigma_hedge`; the market follows GBM with the true volatility
    `config.SIG` and real-world drift `mu`. The call is sold at the Black-Scholes price at the
    true volatility; P&L is measured in money at expiry.
    """
    s0, k, t, r, sig = config.S, config.K, config.T, config.R, config.SIG
    rng = np.random.default_rng(seed)
    dt = t / n_rebal
    spot = np.full(paths, s0)
    cash = np.full(paths, o.bs_price(s0, k, t, r, sig))
    delta = o.bs_greeks(spot, k, t, r, sigma_hedge)["delta"]
    cash -= delta * spot
    for i in range(1, n_rebal + 1):
        z = rng.standard_normal(paths)
        spot = spot * np.exp((mu - 0.5 * sig**2) * dt + sig * np.sqrt(dt) * z)
        cash *= np.exp(r * dt)
        if i < n_rebal:
            new_delta = o.bs_greeks(spot, k, t - i * dt, r, sigma_hedge)["delta"]
            cash -= (new_delta - delta) * spot
            delta = new_delta
    return cash + delta * spot - np.maximum(spot - k, 0.0)
