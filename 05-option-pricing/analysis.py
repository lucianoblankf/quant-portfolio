"""Project 5: option pricing experiments.

Run with:  python analysis.py

1. Monte Carlo error with and without variance reduction
2. Binomial tree convergence and the early-exercise premium of an American put
3. Delta hedging: how the hedging error depends on rebalancing frequency and on the
   volatility used to hedge
4. A real volatility smile: SPY options, implied volatilities from our own solver
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import options as o

HERE = Path(__file__).parent
FIG = HERE / "figures"
RES = HERE / "results"
DATA = HERE / "data"
S, K, T, R, SIG = 100.0, 100.0, 1.0, 0.05, 0.20
pd.set_option("display.width", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.5f}")


def monte_carlo_table() -> pd.DataFrame:
    exact = o.bs_price(S, K, T, R, SIG)
    rows = []
    for n in (1_000, 10_000, 100_000, 1_000_000):
        row = {"n": n}
        for label, kw in (("plain", dict(antithetic=False)),
                          ("antithetic", dict(antithetic=True)),
                          ("antithetic+control", dict(antithetic=True, control_variate=True))):
            price, se = o.mc_price(S, K, T, R, SIG, n=n, seed=11, **kw)
            row[f"{label}_error"] = price - exact
            row[f"{label}_se"] = se
        rows.append(row)
    return pd.DataFrame(rows)


def binomial_table() -> pd.DataFrame:
    exact_c = o.bs_price(S, K, T, R, SIG, "call")
    rows = []
    for n in (10, 25, 50, 100, 250, 500, 1000, 2000):
        eu = o.crr_price(S, K, T, R, SIG, "call", steps=n)
        rows.append({"steps": n, "european_call": eu, "error_vs_BS": eu - exact_c,
                     "american_put": o.crr_price(S, K, T, R, SIG, "put", steps=n, american=True),
                     "european_put": o.crr_price(S, K, T, R, SIG, "put", steps=n)})
    t = pd.DataFrame(rows)
    t["early_exercise_premium"] = t["american_put"] - t["european_put"]
    return t


def delta_hedge(n_rebal: int, sigma_hedge: float, paths=20_000, mu=0.10, seed=5) -> np.ndarray:
    """P&L at expiry of selling one call and delta-hedging at n_rebal equally spaced
    dates, with the delta computed at `sigma_hedge`. The market follows GBM with the
    true volatility SIG and real-world drift mu. The call is sold at the Black-Scholes
    price at SIG; P&L is measured in money at expiry."""
    rng = np.random.default_rng(seed)
    dt = T / n_rebal
    S_t = np.full(paths, S)
    premium = o.bs_price(S, K, T, R, SIG)
    cash = np.full(paths, premium)
    delta = o.bs_greeks(S_t, K, T, R, sigma_hedge)["delta"]
    cash -= delta * S_t
    for i in range(1, n_rebal + 1):
        z = rng.standard_normal(paths)
        S_t = S_t * np.exp((mu - 0.5 * SIG ** 2) * dt + SIG * np.sqrt(dt) * z)
        cash *= np.exp(R * dt)
        if i < n_rebal:
            new_delta = o.bs_greeks(S_t, K, T - i * dt, R, sigma_hedge)["delta"]
            cash -= (new_delta - delta) * S_t
            delta = new_delta
    return cash + delta * S_t - np.maximum(S_t - K, 0.0)


def hedging_tables():
    freq = []
    for n in (4, 12, 26, 52, 126, 252):
        pnl = delta_hedge(n, SIG)
        freq.append({"rebalances": n, "mean": pnl.mean(), "std": pnl.std(), "std_x_sqrt_n": pnl.std() * np.sqrt(n)})
    freq = pd.DataFrame(freq)
    vol = []
    for sh in (0.10, 0.15, 0.20, 0.25, 0.30):
        pnl = delta_hedge(252, sh)
        vol.append({"hedge_vol": sh, "mean": pnl.mean(), "std": pnl.std()})
    return freq, pd.DataFrame(vol)


def real_smile():
    """SPY chain for the expiry closest to 35 days. Cached in data/."""
    f = DATA / "spy_chain.csv"
    if not f.exists():
        import yfinance as yf
        tk = yf.Ticker("SPY")
        spot = float(tk.history(period="5d")["Close"].iloc[-1])
        today = pd.Timestamp.today().normalize()
        exps = pd.to_datetime(tk.options)
        exp = exps[np.argmin(np.abs((exps - today).days - 35))]
        ch = tk.option_chain(exp.strftime("%Y-%m-%d"))
        rf = float(yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1]) / 100
        frames = []
        for kind, df in (("call", ch.calls), ("put", ch.puts)):
            df = df[["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]].copy()
            df["kind"] = kind
            frames.append(df)
        out = pd.concat(frames)
        out["spot"], out["expiry"], out["asof"], out["rf"] = spot, exp.date(), today.date(), rf
        DATA.mkdir(exist_ok=True)
        out.to_csv(f, index=False)
    ch = pd.read_csv(f, parse_dates=["expiry", "asof"])
    spot, rf = ch["spot"].iloc[0], ch["rf"].iloc[0]
    T_ = max((ch["expiry"].iloc[0] - ch["asof"].iloc[0]).days, 1) / 365
    q = 0.013                                              # approximate SPY dividend yield
    ch = ch[(ch["bid"] > 0) & (ch["ask"] > 0)].copy()
    ch["mid"] = (ch["bid"] + ch["ask"]) / 2
    # Use out-of-the-money options only: more liquid and less affected by early exercise.
    ch = ch[((ch["kind"] == "call") & (ch["strike"] >= spot)) | ((ch["kind"] == "put") & (ch["strike"] < spot))]
    ch = ch[(ch["strike"] > 0.85 * spot) & (ch["strike"] < 1.15 * spot)]
    ch["iv"] = [o.implied_vol(m, spot, k, T_, rf, kind, q) for m, k, kind in zip(ch["mid"], ch["strike"], ch["kind"])]
    ch = ch.dropna(subset=["iv"]).sort_values("strike")
    return ch, spot, T_, rf


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    exact_c, exact_p = o.bs_price(S, K, T, R, SIG), o.bs_price(S, K, T, R, SIG, "put")
    print(f"Black-Scholes: call {exact_c:.4f}, put {exact_p:.4f}\n")

    mc = monte_carlo_table()
    print("1. Monte Carlo (error = price - exact; se = standard error)")
    print(mc.to_string(index=False))
    last = mc.iloc[-1]
    print(f"Variance reduction at n=1,000,000: se ratio plain/antithetic = {last['plain_se'] / last['antithetic_se']:.2f}, "
          f"plain/(antithetic+control) = {last['plain_se'] / last['antithetic+control_se']:.2f}\n")
    mc.to_csv(RES / "monte_carlo.csv", index=False)

    bn = binomial_table()
    print("2. Binomial tree")
    print(bn.to_string(index=False), "\n")
    bn.to_csv(RES / "binomial.csv", index=False)

    freq, vol = hedging_tables()
    print("3a. Delta hedging, one short call, hedge vol = true vol (20,000 paths)")
    print(freq.to_string(index=False))
    slope = np.polyfit(np.log(freq["rebalances"]), np.log(freq["std"]), 1)[0]
    print(f"log-log slope of std against rebalances: {slope:.2f} (theory: -0.5)\n")
    print("3b. Daily hedging with the wrong volatility (true vol 20%)")
    print(vol.to_string(index=False), "\n")
    freq.to_csv(RES / "hedging_frequency.csv", index=False)
    vol.to_csv(RES / "hedging_vol_error.csv", index=False)

    # ---- figures -------------------------------------------------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ns = mc["n"].to_numpy()
    for label, col in (("plain", "#E45756"), ("antithetic", "#F58518"), ("antithetic+control", "#4C78A8")):
        ax[0].loglog(ns, mc[f"{label}_se"], "o-", color=col, label=label)
    ax[0].set_xlabel("Simulations")
    ax[0].set_ylabel("Standard error")
    ax[0].set_title("Monte Carlo standard error")
    ax[0].legend()
    ax[1].semilogx(bn["steps"], bn["european_call"] - exact_c, "o-", color="#4C78A8")
    ax[1].axhline(0, color="grey", ls="--")
    ax[1].set_xlabel("Binomial steps")
    ax[1].set_ylabel("Tree price minus Black-Scholes")
    ax[1].set_title("Binomial convergence (European call)")
    fig.tight_layout()
    fig.savefig(FIG / "convergence.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    pnl_a, pnl_b = delta_hedge(12, SIG), delta_hedge(252, SIG)
    bins = np.linspace(-6, 6, 90)
    ax[0].hist(pnl_a, bins=bins, alpha=0.6, color="#E45756", label="12 rebalances")
    ax[0].hist(pnl_b, bins=bins, alpha=0.6, color="#4C78A8", label="252 rebalances")
    ax[0].set_xlabel("Hedging P&L at expiry")
    ax[0].set_title("Delta-hedging error")
    ax[0].legend()
    ax[1].plot(vol["hedge_vol"] * 100, vol["mean"], "o-", color="#4C78A8")
    ax[1].axhline(0, color="grey", ls="--")
    ax[1].axvline(20, color="grey", ls=":")
    ax[1].set_xlabel("Volatility used to hedge (true = 20%)")
    ax[1].set_ylabel("Mean P&L of the option seller")
    ax[1].set_title("Hedging with the wrong volatility")
    fig.tight_layout()
    fig.savefig(FIG / "delta_hedging.png", dpi=150)
    plt.close(fig)

    spots = np.linspace(60, 140, 200)
    fig, axs = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)
    for T_, col in ((0.1, "#E45756"), (0.5, "#F58518"), (1.0, "#4C78A8")):
        g = o.bs_greeks(spots, K, T_, R, SIG, "call")
        for a, key in zip(axs.ravel(), ("delta", "gamma", "vega", "theta")):
            a.plot(spots, g[key], color=col, label=f"T = {T_}")
            a.set_title(key.capitalize())
    axs[0, 0].legend()
    fig.suptitle("Call option Greeks against spot (K = 100, sigma = 20%, r = 5%)")
    fig.tight_layout()
    fig.savefig(FIG / "greeks.png", dpi=150)
    plt.close(fig)

    try:
        ch, spot, T_, rf = real_smile()
        print(f"4. SPY smile: spot {spot:.2f}, T = {T_ * 365:.0f} days, r = {rf:.2%}, {len(ch)} out-of-the-money quotes")
        yahoo = ch["impliedVolatility"].to_numpy()
        both = (yahoo > 0.01) & np.isfinite(yahoo)
        print(f"   ATM-ish implied vol (our solver): {ch.iloc[(ch['strike'] - spot).abs().argmin()]['iv']:.1%}; "
              f"median abs gap to Yahoo's own IV: {np.median(np.abs(ch['iv'].to_numpy()[both] - yahoo[both])):.3f}")
        left = ch[ch["strike"] < 0.95 * spot]["iv"].mean()
        right = ch[ch["strike"] > 1.05 * spot]["iv"].mean()
        print(f"   average IV, strikes below 95% of spot: {left:.1%}; above 105%: {right:.1%}")
        ch.to_csv(RES / "spy_smile.csv", index=False)
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        ax.plot(ch["strike"] / spot, ch["iv"] * 100, "o", ms=3.5, color="#4C78A8", label="Implied vol (our solver)")
        ax.axhline(ch.iloc[(ch["strike"] - spot).abs().argmin()]["iv"] * 100, color="#E45756", ls="--",
                   label="Black-Scholes flat vol (ATM)")
        ax.set_xlabel("Strike / spot")
        ax.set_ylabel("Implied volatility (%)")
        ax.set_title(f"SPY volatility smile, expiry in {T_ * 365:.0f} days")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIG / "spy_smile.png", dpi=150)
        plt.close(fig)
    except Exception as exc:                       # network or data problem: skip, do not fail the script
        print(f"4. SPY smile skipped: {exc}")
    print(f"\nFigures saved to {FIG}")


if __name__ == "__main__":
    main()
