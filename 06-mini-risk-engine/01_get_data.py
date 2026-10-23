"""01: raw prices and Tesouro Direto file (downloaded once), then the factor returns."""

from src import data, reporting

reporting.section("01 Data")

data.download_raw_prices()
data.download_raw_tesouro()

prices = data.read_prices()
yields = data.zero_yield()
returns = data.build_factor_returns(prices, yields)

yields.to_frame().to_parquet("data/processed/zero_yield.parquet")
returns.to_parquet("data/processed/factor_returns.parquet")

reporting.success(
    f"Factor returns: {len(returns)} days, {returns.index.min().date()} to {returns.index.max().date()}"
)
reporting.info(f"3-year zero yield today: {yields.iloc[-1]:.2%}")
