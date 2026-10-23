"""02: bootstrap the zero curve, reprice every input and check the LTN / NTN-F basis."""

import pandas as pd

from src import config, curve as c, data, reporting

reporting.section("02 Bootstrap")

bonds = pd.read_parquet("data/processed/bonds.parquet")
quote_date = pd.Timestamp(config.QUOTE_DATE) if config.QUOTE_DATE else bonds["quote_date"].max()
cv, instruments, yields = data.curve_on(bonds, quote_date)
reporting.info(f"Quote date {quote_date.date()}, valuation (D+1) {cv.valuation}; {len(instruments)} instruments")

# Pillars: zero rate and forward rate from the previous pillar
maturities = sorted({m for _, m, _ in instruments})
previous = 0.0
rows = []
for mat, du, rate in zip(maturities, cv.du, cv.rate):
    rows.append(
        {"maturity": mat, "du": int(du), "years": du / 252, "zero": rate, "forward_from_prev_pillar": cv.forward(previous, du)}
    )
    previous = du
pillars = pd.DataFrame(rows)

# Repricing of the inputs
repricing = pd.DataFrame(
    [
        {
            "bond": f"{kind} {mat}",
            "market_pu": pu,
            "model_pu": c.price(cv, kind, mat),
            "error": c.price(cv, kind, mat) - pu,
            "quoted_yield": yields[(kind, mat)],
        }
        for kind, mat, pu in instruments
    ]
)

# Same-maturity LTN vs NTN-F: yield difference in bp (a cross-check, not used in the fit)
basis = pd.DataFrame(
    [
        {"maturity": mat, "ntnf_minus_ltn_bp": 1e4 * (yields[("NTN-F", mat)] - yields[("LTN", mat)])}
        for mat in maturities
        if ("LTN", mat) in yields and ("NTN-F", mat) in yields
    ]
)

for name, tbl in (("pillars", pillars), ("repricing", repricing), ("basis", basis)):
    reporting.save_table(tbl, name)

reporting.show_table(pillars, "Bootstrapped pillars (annual rate, 252 basis)")
reporting.show_table(repricing, "Repricing of the inputs")
reporting.show_table(basis, "Same-maturity NTN-F minus LTN yield (bp)", digits=1)
