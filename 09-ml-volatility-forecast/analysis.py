"""Project 9: can machine learning beat the HAR model at forecasting Ibovespa volatility?

Run with:  python analysis.py

Target: log of the average daily (Parkinson) variance over the next 5 trading days.
Models: naive, EWMA, HAR (OLS), HAR + extra features (Ridge), random forest, gradient
boosting. Walk-forward evaluation: expanding window, re-fitted every 63 days, first
forecast after 750 days of history.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import volml as v

HERE = Path(__file__).parent
DATA, FIG, RES = HERE / "data", HERE / "figures", HERE / "results"
H = 5
pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")


def load():
    f = DATA / "ohlc.csv"
    if not f.exists():
        import yfinance as yf
        ibov = yf.download("^BVSP", start="2010-01-01", auto_adjust=True, progress=False)
        ibov.columns = ibov.columns.get_level_values(0)
        fx = yf.download("BRL=X", start="2010-01-01", auto_adjust=True, progress=False)
        fx.columns = fx.columns.get_level_values(0)
        out = ibov[["Open", "High", "Low", "Close"]].join(fx["Close"].rename("fx"), how="left")
        DATA.mkdir(exist_ok=True)
        out.to_csv(f)
    d = pd.read_csv(f, index_col=0, parse_dates=True)
    d = d[(d["High"] > d["Low"]) & (d["Low"] > 0)]                   # drop bad rows (zero range)
    return d[["Open", "High", "Low", "Close"]], d["fx"].ffill()


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    ohlc, fx = load()
    data = v.make_dataset(ohlc, fx, h=H)
    all_feats = [c for c in data if c.startswith("f_")]
    har_feats = ["f_logrv_1", "f_logrv_5", "f_logrv_22"]
    print(f"{len(data)} days, {data.index.min().date()} to {data.index.max().date()}; "
          f"{len(all_feats)} features: {', '.join(all_feats)}\n")

    models = {
        "HAR (OLS)": LinearRegression(),
        "HAR + extras (Ridge)": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "Random forest": RandomForestRegressor(n_estimators=200, min_samples_leaf=30, max_features=0.5,
                                               n_jobs=-1, random_state=0),
        "Gradient boosting": HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200,
                                                           min_samples_leaf=50, l2_regularization=1.0,
                                                           random_state=0),
    }
    feats = {"HAR (OLS)": har_feats, "HAR + extras (Ridge)": all_feats,
             "Random forest": all_feats, "Gradient boosting": all_feats}
    res = v.walk_forward(data, models, feats, start=750, refit=63, h=H)
    # Benchmarks that need no fitting
    res["Naive (yesterday)"] = data.loc[res.index, "f_logrv_1"]
    res["EWMA 0.94"] = v.ewma_forecast(data["rv"], 0.94).loc[res.index]
    names = ["Naive (yesterday)", "EWMA 0.94", "HAR (OLS)", "HAR + extras (Ridge)", "Random forest", "Gradient boosting"]
    print(f"Out-of-sample: {len(res)} days, {res.index.min().date()} to {res.index.max().date()}\n")

    # ---- accuracy -----------------------------------------------------------------------------
    def score(frame):
        rows = []
        for n in names:
            rows.append({"model": n, "MSE_log": v.mse_log(frame["y"], frame[n]),
                         "QLIKE": v.qlike(frame["y"], frame[n]), "MZ_R2": v.mz_r2(frame["y"], frame[n])})
        return pd.DataFrame(rows).set_index("model")

    full = score(res)
    print("Out-of-sample accuracy, full period (lower MSE/QLIKE is better; higher R2 is better)")
    print(full.to_string(), "\n")
    crisis = (res.index >= "2020-02-15") & (res.index <= "2020-06-30")
    calm = ~crisis
    print("Calm periods (excluding 2020-02-15 to 2020-06-30)")
    print(score(res[calm]).to_string(), "\n")
    print("COVID window (2020-02-15 to 2020-06-30)")
    print(score(res[crisis]).to_string(), "\n")
    full.to_csv(RES / "accuracy_full.csv")
    score(res[calm]).to_csv(RES / "accuracy_calm.csv")
    score(res[crisis]).to_csv(RES / "accuracy_covid.csv")

    # ---- Diebold-Mariano against HAR --------------------------------------------------------------
    def qloss(n):
        r = np.exp(res["y"] - res[n])
        return (r - np.log(r) - 1).to_numpy()

    dm_rows = []
    for n in names:
        if n == "HAR (OLS)":
            continue
        stat, p = v.diebold_mariano(qloss(n), qloss("HAR (OLS)"), h=H)
        dm_rows.append({"model": n, "DM_stat_vs_HAR": stat, "p_value": p,
                        "better_than_HAR": "yes" if stat < 0 and p < 0.05 else ("worse" if stat > 0 and p < 0.05 else "no difference")})
    dm = pd.DataFrame(dm_rows)
    print("Diebold-Mariano on QLIKE, each model against HAR (negative = model better)")
    print(dm.to_string(index=False), "\n")
    dm.to_csv(RES / "diebold_mariano.csv", index=False)

    # ---- feature importance for the boosting model ----------------------------------------------------
    cut = int(len(data) * 0.8)
    tr, te = data.iloc[:cut - H].dropna(subset=["y"]), data.iloc[cut:].dropna(subset=["y"])
    gb = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50,
                                       l2_regularization=1.0, random_state=0).fit(tr[all_feats], tr["y"])
    pi = permutation_importance(gb, te[all_feats], te["y"], n_repeats=15, random_state=0,
                                scoring="neg_mean_squared_error")
    imp = pd.Series(pi.importances_mean, index=all_feats).sort_values(ascending=False)
    print("Permutation importance of the boosting model (increase in MSE when the feature is shuffled)")
    print(imp.to_string(), "\n")
    imp.to_csv(RES / "feature_importance.csv", header=["mse_increase"])

    # HAR coefficients on the full sample
    har = LinearRegression().fit(data.dropna(subset=["y"])[har_feats], data.dropna(subset=["y"])["y"])
    print("HAR coefficients (full sample):", {k: round(float(c), 3) for k, c in zip(har_feats, har.coef_)}, f"intercept {har.intercept_:.3f}\n")

    # ---- figures ---------------------------------------------------------------------------------------
    ann = lambda lg: 100 * np.sqrt(252 * np.exp(lg))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    w = res.loc["2019-10-01":"2021-03-31"]
    ax.plot(w.index, ann(w["y"]), color="black", lw=1, label="Realised (next 5 days)")
    ax.plot(w.index, ann(w["HAR (OLS)"]), color="#4C78A8", lw=1.3, label="HAR")
    ax.plot(w.index, ann(w["Gradient boosting"]), color="#E45756", lw=1.3, label="Gradient boosting")
    ax.set_ylabel("Annualised volatility (%)")
    ax.set_title("Out-of-sample forecasts through the COVID crash")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "forecast_covid.png", dpi=150)
    plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    full["QLIKE"].sort_values(ascending=False).plot.barh(ax=axs[0], color="#4C78A8")
    axs[0].set_title("QLIKE loss, full period")
    imp.sort_values().plot.barh(ax=axs[1], color="#E45756")
    axs[1].set_title("Boosting: permutation importance")
    fig.tight_layout()
    fig.savefig(FIG / "accuracy_and_importance.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(res["HAR (OLS)"], res["y"], s=4, alpha=0.3, color="#4C78A8")
    lim = [res[["y", "HAR (OLS)"]].min().min(), res[["y", "HAR (OLS)"]].max().max()]
    ax.plot(lim, lim, color="#E45756")
    ax.set_xlabel("HAR forecast (log variance)")
    ax.set_ylabel("Realised (log variance)")
    ax.set_title("HAR forecast vs outcome, out of sample")
    fig.tight_layout()
    fig.savefig(FIG / "har_scatter.png", dpi=150)
    plt.close(fig)
    print(f"Figures saved to {FIG}")


if __name__ == "__main__":
    main()
