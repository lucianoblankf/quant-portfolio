"""Plot helpers for project 1 (plotnine, the grammar of graphics)."""

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    coord_equal,
    geom_abline,
    geom_rect,
    geom_line,
    geom_point,
    ggplot,
    labs,
    scale_y_log10,
    theme_minimal,
)
from scipy import stats


def plot_histogram(returns: np.ndarray, label: str, bins: int = 120):
    """Histogram of returns against the fitted normal, on a log scale so tails are visible.

    Densities are computed here (not by the stat layer) because a log scale applied before
    binning would distort the bars; empty bins are dropped since log(0) is undefined.
    """
    r = np.asarray(returns)
    density, edges = np.histogram(r, bins=bins, density=True)
    floor = 1e-2
    bars = pd.DataFrame({"xmin": edges[:-1], "xmax": edges[1:], "density": density}).query("density > @floor")
    grid = np.linspace(r.min(), r.max(), 500)
    curve = pd.DataFrame({"x": grid, "density": stats.norm.pdf(grid, r.mean(), r.std(ddof=1))})
    return (
        ggplot()
        + geom_rect(bars, aes(xmin="xmin", xmax="xmax", ymin=floor, ymax="density"), fill="#4C78A8", alpha=0.75)
        + geom_line(curve.query("density > @floor"), aes("x", "density"), color="#E45756", size=1)
        + scale_y_log10()
        + labs(
            title=f"{label}: daily log returns vs the normal distribution",
            x="Daily log return",
            y="Density (log scale)",
        )
        + theme_minimal()
    )


def plot_qq(returns: np.ndarray, label: str):
    """QQ plot of standardised returns: points on the line mean normal; an S shape means fat tails."""
    r = np.asarray(returns)
    z = np.sort((r - r.mean()) / r.std(ddof=1))
    frame = pd.DataFrame({"theoretical": stats.norm.ppf((np.arange(len(z)) + 0.5) / len(z)), "observed": z})
    return (
        ggplot(frame, aes("theoretical", "observed"))
        + geom_point(size=0.6, color="#4C78A8")
        + geom_abline(slope=1, intercept=0, color="#E45756")
        + coord_equal()
        + labs(
            title=f"{label}: QQ plot against the normal",
            x="Normal quantiles",
            y="Observed quantiles (standardised)",
        )
        + theme_minimal()
    )
