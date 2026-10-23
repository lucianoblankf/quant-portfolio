"""03: duration, DV01 and key-rate DV01 of the book."""

from datetime import date

import pandas as pd

from src import config, curve as c, data, reporting

reporting.section("03 Risk")

bonds = pd.read_parquet("data/processed/bonds.parquet")
quote_date = pd.Timestamp(config.QUOTE_DATE) if config.QUOTE_DATE else bonds["quote_date"].max()
cv, instruments, _ = data.curve_on(bonds, quote_date)

book = [(kind, date.fromisoformat(mat)) for kind, mat in config.RISK_BOOK]

risk = pd.DataFrame(
    [
        {
            "bond": f"{kind} {mat}",
            "pu": c.price(cv, kind, mat),
            "duration_years": c.macaulay_duration(cv, kind, mat),
            "dv01_per_1000": c.dv01(cv, kind, mat),
            "dv01_pct_of_price_bp": 1e4 * c.dv01(cv, kind, mat) / c.price(cv, kind, mat),
        }
        for kind, mat in book
    ]
)

pillar_labels = [str(m) for m in sorted({m for _, m, _ in instruments})]
krd = pd.DataFrame(
    {f"{kind} {mat}": c.key_rate_dv01(cv, kind, mat) for kind, mat in book}, index=pillar_labels
).rename_axis("pillar")
krd_check = pd.DataFrame(
    {
        "bond": krd.columns,
        "sum_key_rates": krd.sum().to_numpy(),
        "parallel_dv01": [c.dv01(cv, kind, mat) for kind, mat in book],
    }
)

reporting.save_table(risk, "risk")
reporting.save_table(krd.reset_index(), "key_rate_dv01")
reporting.save_table(krd_check, "key_rate_check")

reporting.show_table(risk, "Risk per 1000 of face (DV01 = price gain for a 1 bp fall in all zero rates)")
reporting.show_table(krd.reset_index(), "Key-rate DV01 by pillar (per 1000 of face)")
reporting.show_table(krd_check, "Sum of key-rate DV01 against the parallel DV01")
