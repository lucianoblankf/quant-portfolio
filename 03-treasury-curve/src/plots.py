"""Plot helpers for project 3 (plotnine)."""

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    geom_col,
    geom_line,
    geom_point,
    ggplot,
    labs,
    position_dodge,
    scale_color_manual,
    scale_fill_manual,
    scale_shape_manual,
    theme,
    theme_minimal,
)

from src import curve as c


def plot_zero_forward(cv: c.Curve, yields: dict, valuation, quote_date) -> ggplot:
    """Zero curve, 1-month forward and the quoted yields of the input bonds."""
    x = np.linspace(20, cv.du[-1], 400)
    lines = pd.concat(
        [
            pd.DataFrame({"years": x / 252, "rate": 100 * cv.zero(x), "series": "Zero curve (bootstrapped)"}),
            pd.DataFrame(
                {
                    "years": x[:-1] / 252,
                    "rate": [100 * cv.forward(a, a + 21) for a in x[:-1]],
                    "series": "1-month forward",
                }
            ),
        ]
    )
    points = pd.DataFrame(
        [
            {"years": c.business_days(valuation, mat) / 252, "rate": 100 * y, "bond": f"{kind} quoted yield"}
            for (kind, mat), y in yields.items()
        ]
    )
    return (
        ggplot()
        + geom_line(lines, aes("years", "rate", color="series"), size=1)
        + geom_point(points, aes("years", "rate", shape="bond"), size=3)
        + scale_color_manual(values=["#E45756", "#4C78A8"])
        + scale_shape_manual(values=["o", "s"])
        + labs(title=f"Pre-fixed zero and forward curve, {quote_date.date()}", x="Years", y="% a.a.", color=None, shape=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_snapshots(curves: dict) -> ggplot:
    """Bootstrapped zero curves on several dates."""
    frames = []
    for label, cv in curves.items():
        x = np.linspace(60, cv.du[-1], 300)
        frames.append(pd.DataFrame({"years": x / 252, "rate": 100 * cv.zero(x), "date": label}))
    return (
        ggplot(pd.concat(frames), aes("years", "rate", color="date"))
        + geom_line(size=1)
        + scale_color_manual(values=["#999999", "#F58518", "#4C78A8"][: len(curves)])
        + labs(title="Bootstrapped zero curve on three dates", x="Years", y="Zero rate, % a.a.", color=None)
        + theme_minimal()
    )


def plot_key_rate_dv01(krd: pd.DataFrame, bonds: list) -> ggplot:
    """Key-rate DV01 by pillar for the chosen bonds (columns of `krd`)."""
    long = (
        krd.loc[:, bonds]
        .rename_axis("pillar")
        .reset_index()
        .melt(id_vars="pillar", var_name="bond", value_name="dv01")
        .assign(pillar=lambda d: d["pillar"].str[:4])
    )
    return (
        ggplot(long, aes("pillar", "dv01", fill="bond"))
        + geom_col(position=position_dodge(width=0.8), width=0.75)
        + scale_fill_manual(values=["#4C78A8", "#F58518", "#54A24B"][: len(bonds)])
        + labs(title="Key-rate DV01: where the risk sits on the curve", x="Pillar (maturity year)", y="DV01 per 1000 face", fill=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )
