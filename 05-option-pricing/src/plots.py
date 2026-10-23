"""Plot helpers for project 5 (plotnine)."""

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    facet_wrap,
    geom_histogram,
    geom_hline,
    geom_line,
    geom_point,
    geom_vline,
    ggplot,
    labs,
    scale_color_manual,
    scale_fill_manual,
    scale_x_log10,
    scale_y_log10,
    theme,
    theme_minimal,
)

from src import config
from src import options as o

COLORS = ["#E45756", "#F58518", "#4C78A8"]


def plot_mc_error(mc: pd.DataFrame):
    """Monte Carlo standard error by number of simulations and method."""
    long = pd.concat(
        [mc[["n", f"{m}_se"]].rename(columns={f"{m}_se": "se"}).assign(method=m) for m in ("plain", "antithetic", "antithetic+control")]
    )
    return (
        ggplot(long, aes("n", "se", color="method"))
        + geom_line(size=1)
        + geom_point(size=2.5)
        + scale_x_log10()
        + scale_y_log10()
        + scale_color_manual(values=COLORS)
        + labs(title="Monte Carlo standard error", x="Simulations", y="Standard error", color=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_tree_convergence(tree: pd.DataFrame):
    """Binomial tree price minus Black-Scholes for the European call."""
    return (
        ggplot(tree, aes("steps", "error_vs_bs"))
        + geom_hline(yintercept=0, linetype="dashed", color="grey")
        + geom_line(color="#4C78A8", size=1)
        + geom_point(color="#4C78A8", size=2.5)
        + scale_x_log10()
        + labs(title="Binomial convergence (European call)", x="Binomial steps", y="Tree price minus Black-Scholes")
        + theme_minimal()
    )


def plot_hedging_error(pnl: pd.DataFrame):
    """Distribution of the delta-hedging P&L for two rebalancing frequencies."""
    return (
        ggplot(pnl, aes("pnl", fill="rebalances"))
        + geom_histogram(bins=90, alpha=0.6, position="identity")
        + scale_fill_manual(values=["#E45756", "#4C78A8"])
        + labs(title="Delta-hedging error", x="Hedging P&L at expiry", y="Paths", fill=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_wrong_vol(vol: pd.DataFrame):
    """Mean P&L of the option seller when hedging with the wrong volatility."""
    return (
        ggplot(vol.assign(hedge_vol_pct=lambda d: 100 * d["hedge_vol"]), aes("hedge_vol_pct", "mean"))
        + geom_hline(yintercept=0, linetype="dashed", color="grey")
        + geom_vline(xintercept=100 * config.SIG, linetype="dotted", color="grey")
        + geom_line(color="#4C78A8", size=1)
        + geom_point(color="#4C78A8", size=2.5)
        + labs(
            title="Hedging with the wrong volatility",
            x="Volatility used to hedge (%, true = 20%)",
            y="Mean P&L of the option seller",
        )
        + theme_minimal()
    )


def plot_greeks():
    """Call Greeks against spot for three maturities."""
    spots = np.linspace(60, 140, 200)
    frames = []
    for maturity in (0.1, 0.5, 1.0):
        g = o.bs_greeks(spots, config.K, maturity, config.R, config.SIG, "call")
        for name in ("delta", "gamma", "vega", "theta"):
            frames.append(pd.DataFrame({"spot": spots, "value": g[name], "greek": name.capitalize(), "maturity": f"T = {maturity}"}))
    return (
        ggplot(pd.concat(frames), aes("spot", "value", color="maturity"))
        + geom_line(size=0.9)
        + facet_wrap("greek", scales="free_y")
        + scale_color_manual(values=COLORS)
        + labs(title="Call option Greeks against spot (K = 100, sigma = 20%, r = 5%)", x="Spot", y=None, color=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_smile(smile: pd.DataFrame, atm_vol: float, days: float):
    """Implied volatility against moneyness, with the flat Black-Scholes volatility."""
    return (
        ggplot(smile.assign(moneyness=lambda d: d["strike"] / d["spot"], iv_pct=lambda d: 100 * d["iv"]), aes("moneyness", "iv_pct"))
        + geom_point(color="#4C78A8", size=1.5)
        + geom_hline(yintercept=100 * atm_vol, linetype="dashed", color="#E45756")
        + labs(
            title=f"SPY volatility smile, expiry in {days:.0f} days",
            subtitle="Dashed line: flat Black-Scholes volatility (at the money)",
            x="Strike / spot",
            y="Implied volatility (%)",
        )
        + theme_minimal()
    )
