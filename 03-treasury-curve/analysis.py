"""Project 3: bootstrap the Brazilian pre-fixed zero curve and measure bond risk.

Run with:  python analysis.py [YYYY-MM-DD]

Reads Tesouro Direto prices (LTN and NTN-F) from Tesouro Transparente, bootstraps a
zero curve for the chosen date (default: latest in the file), reprices every input,
and computes duration, DV01 and key-rate DV01. Data is cached in data/.
"""

import sys
import urllib.request
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import curve as c

HERE = Path(__file__).parent
DATA = HERE / "data" / "tesouro_direto.csv"
FIG = HERE / "figures"
RES = HERE / "results"
URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
       "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
KIND = {"Tesouro Prefixado": "LTN", "Tesouro Prefixado com Juros Semestrais": "NTN-F"}


def load() -> pd.DataFrame:
    if not DATA.exists():
        DATA.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(URL, DATA)
    d = pd.read_csv(DATA, sep=";", decimal=",")
    d = d[d["Tipo Titulo"].isin(KIND)].copy()
    d["kind"] = d["Tipo Titulo"].map(KIND)
    d["base"] = pd.to_datetime(d["Data Base"], dayfirst=True)
    d["maturity"] = pd.to_datetime(d["Data Vencimento"], dayfirst=True)
    return d


def market_on(d: pd.DataFrame, base: pd.Timestamp):
    """Instruments quoted on `base`, and the settlement date (next business day).

    Since 2024 the published PUs reconcile to the quoted yields only when discounted from
    the next business day, so that is the valuation date."""
    x = d[d["base"] == base]
    settle = c.next_business_day(base.date())
    inst = [(r.kind, r.maturity.date(), float(r["PU Compra Manha"])) for _, r in x.iterrows()]
    yields = {(r.kind, r.maturity.date()): r["Taxa Compra Manha"] / 100 for _, r in x.iterrows()}
    return settle, inst, yields


def pillar_table(cv: c.Curve) -> pd.DataFrame:
    """Zero rate at each pillar and the forward rate from the previous pillar."""
    rows, prev = [], 0.0
    for du, r in zip(cv.du, cv.rate):
        rows.append({"du": int(du), "years": du / 252, "zero": r, "forward_from_prev_pillar": cv.forward(prev, du)})
        prev = du
    return pd.DataFrame(rows)


def main() -> None:
    d = load()
    last = pd.Timestamp(sys.argv[1]) if len(sys.argv) > 1 else d["base"].max()
    settle, inst, yields = market_on(d, last)
    cv = c.bootstrap(settle, inst)
    print(f"Quote date {last.date()}, valuation (D+1) {settle}; {len(inst)} instruments\n")

    # ---- pillars ------------------------------------------------------------------------
    pil = pillar_table(cv)
    pil.insert(0, "maturity", sorted({m for k, m, _ in inst}))
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda v: f"{v:,.4f}")
    print("Bootstrapped pillars (zero = annual rate, 252 basis)")
    print(pil.to_string(index=False), "\n")

    # ---- repricing ----------------------------------------------------------------------
    rows = []
    for kind, mat, pu in inst:
        model = c.price(cv, kind, mat)
        rows.append({"bond": f"{kind} {mat}", "market_pu": pu, "model_pu": model, "error": model - pu,
                     "quoted_yield": yields[(kind, mat)]})
    rep = pd.DataFrame(rows)
    print("Repricing of the inputs")
    print(rep.to_string(index=False), "\n")

    # Basis between LTN and NTN-F with the same maturity (cross-check not used in the fit).
    print("Same-maturity LTN vs NTN-F: yield difference (NTN-F minus LTN), bp")
    for mat in sorted({m for k, m, _ in inst}):
        if ("LTN", mat) in yields and ("NTN-F", mat) in yields:
            print(f"  {mat}: {1e4 * (yields[('NTN-F', mat)] - yields[('LTN', mat)]):+.1f} bp")
    print()

    # ---- risk ---------------------------------------------------------------------------
    book = [("LTN", date(2029, 1, 1)), ("LTN", date(2032, 1, 1)),
            ("NTN-F", date(2029, 1, 1)), ("NTN-F", date(2033, 1, 1)), ("NTN-F", date(2037, 1, 1))]
    risk = pd.DataFrame([{
        "bond": f"{k} {m}", "pu": c.price(cv, k, m), "duration_years": c.macaulay_duration(cv, k, m),
        "dv01_per_1000": c.dv01(cv, k, m), "dv01_pct_of_price_bp": 1e4 * c.dv01(cv, k, m) / c.price(cv, k, m),
    } for k, m in book])
    print("Risk per 1000 of face (DV01 = price gain for a 1 bp fall in all zero rates)")
    print(risk.to_string(index=False), "\n")

    krd = pd.DataFrame({f"{k} {m}": c.key_rate_dv01(cv, k, m) for k, m in book},
                       index=[str(m) for m in sorted({m for _, m, _ in inst})])
    print("Key-rate DV01 by pillar (per 1000 of face)")
    print(krd.to_string(), "\n")
    print("Sum of key-rate DV01 vs parallel DV01:",
          ", ".join(f"{col}: {krd[col].sum():.4f} / {c.dv01(cv, *b):.4f}" for col, b in zip(krd.columns, book)))

    # ---- curve through time ------------------------------------------------------------------
    snaps = {}
    for dt in ("2024-01-02", "2025-01-02", str(last.date())):
        b = pd.Timestamp(dt)
        if (d["base"] == b).any():
            s, i, _ = market_on(d, b)
            snaps[dt] = c.bootstrap(s, i)

    RES.mkdir(exist_ok=True)
    pil.to_csv(RES / "pillars.csv", index=False)
    rep.to_csv(RES / "repricing.csv", index=False)
    risk.to_csv(RES / "risk.csv", index=False)
    krd.to_csv(RES / "key_rate_dv01.csv")

    # ---- figures -------------------------------------------------------------------------------
    FIG.mkdir(exist_ok=True)
    x = np.linspace(20, cv.du[-1], 400)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x / 252, 100 * cv.zero(x), color="#4C78A8", lw=2, label="Zero curve (bootstrapped)")
    fwd = [cv.forward(a, a + 21) for a in x[:-1]]
    ax.plot(x[:-1] / 252, 100 * np.array(fwd), color="#E45756", lw=1.2, label="1-month forward")
    for kind, col, mk in (("LTN", "black", "o"), ("NTN-F", "#54A24B", "s")):
        pts = [(c.business_days(settle, m) / 252, 100 * y) for (k, m), y in yields.items() if k == kind]
        ax.scatter(*zip(*pts), color=col, marker=mk, zorder=5, label=f"{kind} quoted yield")
    ax.set_xlabel("Years")
    ax.set_ylabel("% a.a.")
    ax.set_title(f"Pre-fixed zero and forward curve, {last.date()}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "zero_forward_curve.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for (dt, cvx), col in zip(snaps.items(), ("#999999", "#F58518", "#4C78A8")):
        xx = np.linspace(60, cvx.du[-1], 300)
        ax.plot(xx / 252, 100 * cvx.zero(xx), color=col, lw=2, label=dt)
    ax.set_xlabel("Years")
    ax.set_ylabel("Zero rate, % a.a.")
    ax.set_title("Bootstrapped zero curve on three dates")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "curve_snapshots.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    cols = ["NTN-F 2033-01-01", "NTN-F 2037-01-01", "LTN 2029-01-01"]
    w = 0.27
    for j, col in enumerate(cols):
        ax.bar(np.arange(len(krd)) + (j - 1) * w, krd[col], w, label=col)
    ax.set_xticks(np.arange(len(krd)))
    ax.set_xticklabels([i[:4] for i in krd.index])
    ax.set_xlabel("Pillar (maturity year)")
    ax.set_ylabel("DV01 per 1000 face")
    ax.set_title("Key-rate DV01: where the risk sits on the curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "key_rate_dv01.png", dpi=150)
    plt.close(fig)
    print(f"\nFigures saved to {FIG}")


if __name__ == "__main__":
    main()
