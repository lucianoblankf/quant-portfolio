"""Plot helpers for project 9 (plotnine)."""

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    coord_flip,
    geom_abline,
    geom_col,
    geom_line,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)


def annualised_vol(log_variance) -> np.ndarray:
    """Annualised volatility in percent from the log of the mean daily variance."""
    return 100 * np.sqrt(252 * np.exp(np.asarray(log_variance)))


def plot_forecast_window(forecasts: pd.DataFrame, start: str, end: str):
    """Realised volatility against the HAR and boosting forecasts over a window of dates."""
    window = forecasts.loc[start:end]
    long = pd.concat(
        [
            pd.DataFrame({"date": window.index, "vol": annualised_vol(window[col]), "series": label})
            for col, label in (("y", "Realised (next 5 days)"), ("HAR (OLS)", "HAR"), ("Gradient boosting", "Gradient boosting"))
        ]
    )
    return (
        ggplot(long, aes("date", "vol", color="series"))
        + geom_line(size=0.8)
        + scale_color_manual(values={"Realised (next 5 days)": "black", "HAR": "#4C78A8", "Gradient boosting": "#E45756"})
        + labs(title="Out-of-sample forecasts through the COVID crash", x="", y="Annualised volatility (%)", color=None)
        + theme_minimal()
        + theme(legend_position="bottom")
    )


def plot_qlike(accuracy: pd.DataFrame):
    """QLIKE loss by model, full out-of-sample period."""
    frame = accuracy.sort_values("qlike")
    frame["model"] = pd.Categorical(frame["model"], categories=frame["model"][::-1], ordered=True)
    return (
        ggplot(frame, aes("model", "qlike"))
        + geom_col(fill="#4C78A8")
        + coord_flip()
        + labs(title="QLIKE loss, full period (lower is better)", x="", y="QLIKE")
        + theme_minimal()
    )


def plot_importance(importance: pd.DataFrame):
    """Permutation importance of the boosting model."""
    frame = importance.sort_values("mse_increase")
    frame["feature"] = pd.Categorical(frame["feature"], categories=frame["feature"], ordered=True)
    return (
        ggplot(frame, aes("feature", "mse_increase"))
        + geom_col(fill="#E45756")
        + coord_flip()
        + labs(title="Boosting: permutation importance", x="", y="Increase in MSE when shuffled")
        + theme_minimal()
    )


def plot_har_scatter(forecasts: pd.DataFrame):
    """HAR forecast against the outcome (log variance), out of sample."""
    return (
        ggplot(forecasts.rename(columns={"HAR (OLS)": "har"}), aes("har", "y"))
        + geom_point(size=0.8, alpha=0.3, color="#4C78A8")
        + geom_abline(slope=1, intercept=0, color="#E45756")
        + labs(title="HAR forecast vs outcome, out of sample", x="HAR forecast (log variance)", y="Realised (log variance)")
        + theme_minimal()
    )
