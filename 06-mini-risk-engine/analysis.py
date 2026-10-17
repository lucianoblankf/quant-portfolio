"""Project 6: a mini risk engine on a Brazilian multi-asset portfolio.

Run with:  python analysis.py

Portfolio of R$ 1.2 million: four Brazilian stocks, a USD position and a 3-year
pre-fixed zero-coupon bond (LTN-style). Risk factors come from Yahoo Finance (stocks, USD/BRL)
and Tesouro Direto yields (the 3-year zero rate, interpolated between LTNs).
Outputs: VaR / ES by four methods, component VaR, stress tests and a backtest.
"""

import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import engine as eng

HERE = Path(__file__).parent
DATA, FIG, RES = HERE / "data", HERE / "figures", HERE / "results"
TESOURO = DATA / "tesouro_direto.csv"
URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
       "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
TICKERS = {"PETR4.SA": "PETR4", "VALE3.SA": "VALE3", "ITUB4.SA": "ITUB4", "WEGE3.SA": "WEGE3", "BRL=X": "USDBRL"}
TENOR = 3.0
pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")


def load_prices() -> pd.DataFrame:
    f = DATA / "prices.csv"
    if not f.exists():
        import yfinance as yf
        raw = yf.download(list(TICKERS), start="2015-01-01", auto_adjust=True, progress=False)["Close"]
        DATA.mkdir(exist_ok=True)
        raw.rename(columns=TICKERS).to_csv(f)
    return pd.read_csv(f, index_col=0, parse_dates=True)


def zero_yield_3y() -> pd.Series:
    """Daily 3-year zero rate, linear interpolation of LTN yields around 3 years."""
    if not TESOURO.exists():
        DATA.mkdir(exist_ok=True)
        urllib.request.urlretrieve(URL, TESOURO)
    d = pd.read_csv(TESOURO, sep=";", decimal=",")
    d = d[d["Tipo Titulo"] == "Tesouro Prefixado"].copy()
    d["base"] = pd.to_datetime(d["Data Base"], dayfirst=True)
    d["ttm"] = (pd.to_datetime(d["Data Vencimento"], dayfirst=True) - d["base"]).dt.days / 365.25
    d["y"] = d["Taxa Compra Manha"] / 100
    out = {}
    for day, g in d.groupby("base"):
        g = g.sort_values("ttm")
        if g["ttm"].min() <= TENOR <= g["ttm"].max() and len(g) >= 2:
            out[day] = np.interp(TENOR, g["ttm"], g["y"])
    return pd.Series(out).sort_index()


def build_returns():
    px = load_prices()[list(TICKERS.values())].dropna()
    ret = np.log(px).diff().dropna()
    y = zero_yield_3y()
    dy = y.diff()
    gap = pd.Series(y.index, index=y.index).diff().dt.days
    dy = dy[gap <= 4]                                     # only changes between consecutive trading days
    ret = ret.join(dy.rename("rate"), how="inner").dropna()
    return ret, y


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    ret, y = build_returns()
    print(f"Factor returns: {len(ret)} days, {ret.index.min().date()} to {ret.index.max().date()}\n")

    pf = eng.Portfolio(
        equity={"PETR4": 250_000, "VALE3": 200_000, "ITUB4": 200_000, "WEGE3": 100_000},
        fx={"USDBRL": 150_000},
        bond_value=300_000, bond_years=TENOR, bond_yield=float(y.iloc[-1]), rate_factor="rate")
    print(f"Portfolio value R$ {pf.value:,.0f}; 3y zero yield today {pf.bond_yield:.2%}\n")

    # ---- VaR / ES by method ------------------------------------------------------------------
    cov_s = ret[pf.factors].cov()
    cov_e = eng.ewma_cov(ret[pf.factors], 0.94)
    rows = []
    for alpha in (0.95, 0.99):
        results = {
            "Historical (500d)": eng.historical(pf, ret, 500, alpha),
            "Historical (full sample)": eng.historical(pf, ret, None, alpha),
            "Delta-normal (full sample cov)": eng.delta_normal(pf, cov_s, alpha),
            "Delta-normal (EWMA 0.94)": eng.delta_normal(pf, cov_e, alpha),
            "Monte Carlo t(5), sample cov": eng.monte_carlo_t(pf, cov_s, nu=5, alpha=alpha),
        }
        for k, (v, es) in results.items():
            rows.append({"method": k, "confidence": f"{alpha:.0%}", "VaR": v, "VaR_pct": v / pf.value,
                         "ES": es, "ES_pct": es / pf.value})
    tbl = pd.DataFrame(rows)
    print("1-day VaR and ES (R$)")
    print(tbl.to_string(index=False), "\n")
    tbl.to_csv(RES / "var_es.csv", index=False)

    # ---- component VaR --------------------------------------------------------------------------
    comp = eng.component_var(pf, cov_s, 0.99)
    print("Delta-normal 99% VaR decomposition (sample covariance)")
    print(comp.to_string(), f"\nSum of components: {comp['component_var'].sum():,.0f}\n")
    comp.to_csv(RES / "component_var.csv")
    stand_alone = pd.Series({f: abs(e) * np.sqrt(cov_s.loc[f, f]) * 2.3263 for f, e in pf.exposures().items()})
    print(f"Sum of stand-alone VaRs: {stand_alone.sum():,.0f} vs portfolio {comp['component_var'].sum():,.0f} "
          f"(diversification benefit {1 - comp['component_var'].sum() / stand_alone.sum():.0%})\n")

    # ---- stress -----------------------------------------------------------------------------------
    day, pnl5 = eng.worst_window(pf, ret, 5)
    day1, pnl1 = eng.worst_window(pf, ret, 1)
    stress = {
        "Worst 1 day in sample": (day1.date(), pnl1),
        "Worst 5-day window in sample": (day.date(), pnl5),
        "Equities -30%": ("hypothetical", eng.stress(pf, {k: np.log(0.7) for k in pf.equity})),
        "USD/BRL +20%": ("hypothetical", eng.stress(pf, {"USDBRL": np.log(1.2)})),
        "Rates +300 bp": ("hypothetical", eng.stress(pf, {"rate": 0.03})),
        "Combined: equities -25%, USD +15%, rates +250 bp": (
            "hypothetical", eng.stress(pf, {**{k: np.log(0.75) for k in pf.equity}, "USDBRL": np.log(1.15), "rate": 0.025})),
    }
    st = pd.DataFrame([{"scenario": k, "date": d, "pnl": p, "pnl_pct": p / pf.value} for k, (d, p) in stress.items()])
    print("Stress tests")
    print(st.to_string(index=False), "\n")
    st.to_csv(RES / "stress.csv", index=False)

    # ---- backtest ------------------------------------------------------------------------------------
    bt_rows, series = [], {}
    for method in ("hist", "normal", "ewma"):
        v, p = eng.rolling_var(pf, ret, method, 0.99, window=500)
        series[method] = (v, p)
        br = p < -v
        lr, pv = eng.kupiec(int(br.sum()), len(br), 0.01)
        last = br.tail(250).sum()
        bt_rows.append({"method": method, "days": len(br), "breaches": int(br.sum()), "expected": len(br) * 0.01,
                        "kupiec_p": pv, "last_250_breaches": int(last),
                        "basel_zone": "green" if last <= 4 else ("yellow" if last <= 9 else "red")})
    bt = pd.DataFrame(bt_rows)
    print("Backtest of the 99% 1-day VaR (portfolio P&L at today's positions)")
    print(bt.to_string(index=False), "\n")
    bt.to_csv(RES / "backtest.csv", index=False)

    # ---- figures -----------------------------------------------------------------------------------
    pnl = pf.pnl(ret[pf.factors].tail(500))
    v99, es99 = eng.historical(pf, ret, 500, 0.99)
    dn99 = eng.delta_normal(pf, cov_s, 0.99)[0]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(pnl / 1e3, bins=60, color="#4C78A8", alpha=0.8)
    for val, lab, col in ((-v99, f"Historical VaR 99%: R$ {v99 / 1e3:,.0f}k", "#E45756"),
                          (-es99, f"Expected shortfall 99%: R$ {es99 / 1e3:,.0f}k", "#B22222"),
                          (-dn99, f"Delta-normal VaR 99%: R$ {dn99 / 1e3:,.0f}k", "#F58518")):
        ax.axvline(val / 1e3, color=col, lw=2, label=lab)
    ax.set_xlabel("Daily P&L (R$ thousand)")
    ax.set_ylabel("Days")
    ax.set_title("Portfolio P&L, last 500 days of factor moves")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "pnl_distribution.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4))
    comp["component_var"].sort_values().plot.barh(ax=ax, color="#4C78A8")
    ax.set_xlabel("Contribution to 99% VaR (R$)")
    ax.set_title("Component VaR by risk factor")
    fig.tight_layout()
    fig.savefig(FIG / "component_var.png", dpi=150)
    plt.close(fig)

    v_h, p_h = series["hist"]
    v_e, _ = series["ewma"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(p_h.index, p_h / 1e3, color="grey", lw=0.6, label="Daily P&L")
    ax.plot(v_h.index, -v_h / 1e3, color="#E45756", lw=1.2, label="-VaR historical (500d)")
    ax.plot(v_e.index, -v_e / 1e3, color="#4C78A8", lw=1.2, label="-VaR EWMA")
    ax.set_ylabel("R$ thousand")
    ax.set_title("99% VaR forecasts against realised P&L")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "backtest.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    s = st.sort_values("pnl")
    ax.barh(s["scenario"], s["pnl"] / 1e3, color="#E45756")
    ax.set_xlabel("P&L (R$ thousand)")
    ax.set_title("Stress scenarios")
    fig.tight_layout()
    fig.savefig(FIG / "stress.png", dpi=150)
    plt.close(fig)
    print(f"Figures saved to {FIG}")


if __name__ == "__main__":
    main()
