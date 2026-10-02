"""Project 1: are Brazilian market returns normal, and what does that do to VaR?

Run with:  python analysis.py

Downloads daily prices for the Ibovespa and USD/BRL, then uses the functions
in risk.py to produce a statistics table, a VaR comparison and two figures.
Prices are cached in data/prices.csv so the download happens only once.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import risk

HERE = Path(__file__).parent
DATA_FILE = HERE / "data" / "prices.csv"
FIG_DIR = HERE / "figures"

TICKERS = {"^BVSP": "Ibovespa", "BRL=X": "USD/BRL"}
START = "2010-01-01"
ALPHAS = (0.95, 0.99)


def load_prices() -> pd.DataFrame:
    """Daily closing prices, one column per asset. Uses the local cache if present."""
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, index_col=0, parse_dates=True)

    import yfinance as yf

    raw = yf.download(list(TICKERS), start=START, auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError("Download returned no data. Check your connection and try again.")
    prices = raw["Close"].rename(columns=TICKERS)[list(TICKERS.values())]
    prices.index.name = "date"

    DATA_FILE.parent.mkdir(exist_ok=True)
    prices.to_csv(DATA_FILE)
    return prices


def stats_table(returns: dict) -> pd.DataFrame:
    rows = {}
    for name, r in returns.items():
        s = risk.summary_stats(r)
        jb, p = risk.jarque_bera(r)
        s["jarque_bera"] = jb
        s["jb_p_value"] = p
        rows[name] = s
    return pd.DataFrame(rows)


def var_table(returns: dict) -> pd.DataFrame:
    rows = []
    for name, r in returns.items():
        for alpha in ALPHAS:
            hist = risk.historical_var(r, alpha)
            param = risk.parametric_var(r, alpha)
            rows.append({
                "asset": name,
                "confidence": f"{alpha:.0%}",
                "historical_var": hist,
                "parametric_var": param,
                "hist / param": hist / param,
                "historical_es": risk.historical_es(r, alpha),
                # How often was the normal VaR actually exceeded?
                "param_breach_rate": float((r < -param).mean()),
                "expected_breach_rate": 1 - alpha,
            })
    return pd.DataFrame(rows).set_index(["asset", "confidence"])


def plot_histogram(name: str, r: pd.Series) -> None:
    """Histogram against the fitted normal, on a log scale so the tails are visible."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(r, bins=120, density=True, color="#4C78A8", alpha=0.75, label="Observed returns")
    x = np.linspace(r.min(), r.max(), 500)
    ax.plot(x, stats.norm.pdf(x, r.mean(), r.std()), color="#E45756", lw=2,
            label="Normal with same mean and volatility")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-2)
    ax.set_title(f"{name}: daily log returns vs the normal distribution")
    ax.set_xlabel("Daily log return")
    ax.set_ylabel("Density (log scale)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"hist_{slug(name)}.png", dpi=150)
    plt.close(fig)


def plot_qq(name: str, r: pd.Series) -> None:
    """QQ plot: points on the line mean normal; an S shape means fat tails."""
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    stats.probplot((r - r.mean()) / r.std(), dist="norm", plot=ax)
    ax.set_title(f"{name}: QQ plot against the normal")
    ax.set_xlabel("Normal quantiles")
    ax.set_ylabel("Observed quantiles (standardised)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"qq_{slug(name)}.png", dpi=150)
    plt.close(fig)


def slug(name: str) -> str:
    return name.lower().replace("/", "").replace(" ", "_")


def main() -> None:
    prices = load_prices()
    returns = {name: risk.log_returns(prices[name].dropna()) for name in prices.columns}

    first = min(r.index.min() for r in returns.values()).date()
    last = max(r.index.max() for r in returns.values()).date()
    print(f"\nSample: {first} to {last}\n")

    pd.set_option("display.float_format", lambda v: f"{v:,.4f}")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    print("Descriptive statistics")
    print(stats_table(returns), "\n")

    print("1-day VaR and ES (as a fraction of position value)")
    print(var_table(returns), "\n")

    FIG_DIR.mkdir(exist_ok=True)
    for name, r in returns.items():
        plot_histogram(name, r)
        plot_qq(name, r)
    print(f"Figures saved to {FIG_DIR}")


if __name__ == "__main__":
    main()
