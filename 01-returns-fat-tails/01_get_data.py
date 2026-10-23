"""01: download the raw prices (once) and build the processed log returns."""

from pathlib import Path

from src import data, reporting, risk

reporting.section("01 Data")

data.download_raw_prices()
prices = data.read_raw_prices()

# One row per asset and date; each asset's returns use only its own non-missing prices.
returns = (
    prices.melt(id_vars="date", var_name="asset", value_name="price")
    .dropna(subset=["price"])
    .sort_values(["asset", "date"])
    .assign(
        log_return=lambda d: d.groupby("asset")["price"].transform(
            lambda p: risk.log_returns(p).reindex(p.index)
        )
    )
    .dropna(subset=["log_return"])
    .reset_index(drop=True)
)

Path("data/processed").mkdir(parents=True, exist_ok=True)
returns.to_parquet("data/processed/returns.parquet", index=False)

reporting.success(
    f"{len(returns)} returns saved ({returns['date'].min().date()} to {returns['date'].max().date()})"
)
