"""02: Monte Carlo variance reduction and binomial tree convergence."""

import pandas as pd

from src import config, reporting
from src import options as o

reporting.section("02 Pricing experiments")

s, k, t, r, sig = config.S, config.K, config.T, config.R, config.SIG
exact_call = o.bs_price(s, k, t, r, sig)
exact_put = o.bs_price(s, k, t, r, sig, "put")
reporting.info(f"Black-Scholes: call {exact_call:.4f}, put {exact_put:.4f}")

# Monte Carlo: error against the exact price and standard error, three variance-reduction settings
settings = {
    "plain": {"antithetic": False},
    "antithetic": {"antithetic": True},
    "antithetic+control": {"antithetic": True, "control_variate": True},
}
mc_rows = []
for n in config.MC_SIZES:
    row = {"n": n}
    for label, kwargs in settings.items():
        price, se = o.mc_price(s, k, t, r, sig, n=n, seed=config.SEED_MONTE_CARLO, **kwargs)
        row[f"{label}_error"] = price - exact_call
        row[f"{label}_se"] = se
    mc_rows.append(row)
mc = pd.DataFrame(mc_rows)
reporting.save_table(mc, "monte_carlo")
reporting.show_table(mc, "Monte Carlo (error = price - exact; se = standard error)", digits=5)
last = mc.iloc[-1]
reporting.info(
    f"At n = {int(last['n']):,}: se ratio plain / antithetic = {last['plain_se'] / last['antithetic_se']:.2f}, "
    f"plain / (antithetic + control) = {last['plain_se'] / last['antithetic+control_se']:.2f}"
)

# Binomial tree: European call error and American put early-exercise premium
tree_rows = []
for steps in config.TREE_STEPS:
    european_call = o.crr_price(s, k, t, r, sig, "call", steps=steps)
    american_put = o.crr_price(s, k, t, r, sig, "put", steps=steps, american=True)
    european_put = o.crr_price(s, k, t, r, sig, "put", steps=steps)
    tree_rows.append(
        {
            "steps": steps,
            "european_call": european_call,
            "error_vs_bs": european_call - exact_call,
            "american_put": american_put,
            "european_put": european_put,
            "early_exercise_premium": american_put - european_put,
        }
    )
tree = pd.DataFrame(tree_rows)
reporting.save_table(tree, "binomial")
reporting.show_table(tree, "Binomial tree", digits=5)
