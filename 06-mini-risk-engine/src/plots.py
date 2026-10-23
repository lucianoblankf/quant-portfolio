"""Plot helpers for project 6 (plotnine)."""

import pandas as pd
from plotnine import (
    aes,
    coord_flip,
    geom_col,
    geom_histogram,
    geom_line,
    geom_vline,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)


def plot_pnl_distribution(pnl: pd.Series, lines: dict):
    """Histogram of daily P&L (R$ thousand) with vertical lines for VaR / ES measures.

    `lines` maps a label to a positive loss in R$ (drawn at minus the loss).
    """
    marks = pd.DataFrame({"label": list(lines), "x": [-v / 1e3 for v in lines.values()]})
    return (
        ggplot(pd.DataFrame({"pnl": pnl.to_numpy() / 1e3}), aes("pnl"))
        + geom_histogram(bins=60, fill="#4C78A8", alpha=0.8)
        + geom_vline(marks, aes(xintercept="x", color="label"), size=1.1)
        + scale_color_manual(values=["#E45756", "#B22222", "#F58518"][: len(lines)])
        + labs(title="Portfolio P&L, last 500 days of factor moves", x="Daily P&L (R$ thousand)", y="Days", color=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_component_var(components: pd.DataFrame):
    """Contribution of each risk factor to the 99% VaR."""
    frame = components.reset_index(names="factor").sort_values("component_var")
    frame["factor"] = pd.Categorical(frame["factor"], categories=frame["factor"], ordered=True)
    return (
        ggplot(frame, aes("factor", "component_var"))
        + geom_col(fill="#4C78A8")
        + coord_flip()
        + labs(title="Component VaR by risk factor", x="", y="Contribution to 99% VaR (R$)")
        + theme_minimal()
    )


def plot_backtest(series: pd.DataFrame):
    """Daily P&L against the 99% VaR forecasts (historical and EWMA)."""
    long = pd.concat(
        [
            series[["date", "pnl"]].rename(columns={"pnl": "value"}).assign(series="Daily P&L"),
            series[["date", "var_hist"]].rename(columns={"var_hist": "value"}).assign(series="-VaR historical (500d)").assign(
                value=lambda d: -d["value"]
            ),
            series[["date", "var_ewma"]].rename(columns={"var_ewma": "value"}).assign(series="-VaR EWMA").assign(
                value=lambda d: -d["value"]
            ),
        ]
    ).assign(value=lambda d: d["value"] / 1e3)
    return (
        ggplot(long, aes("date", "value", color="series"))
        + geom_line(size=0.4)
        + scale_color_manual(values={"Daily P&L": "grey", "-VaR historical (500d)": "#E45756", "-VaR EWMA": "#4C78A8"})
        + labs(title="99% VaR forecasts against realised P&L", x="", y="R$ thousand", color=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_stress(stress: pd.DataFrame):
    """P&L of each stress scenario (R$ thousand)."""
    frame = stress.sort_values("pnl").assign(pnl_k=lambda d: d["pnl"] / 1e3)
    frame["scenario"] = pd.Categorical(frame["scenario"], categories=frame["scenario"], ordered=True)
    return (
        ggplot(frame, aes("scenario", "pnl_k"))
        + geom_col(fill="#E45756")
        + coord_flip()
        + labs(title="Stress scenarios", x="", y="P&L (R$ thousand)")
        + theme_minimal()
    )
