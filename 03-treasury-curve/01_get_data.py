"""01: download the raw Tesouro Direto file (once) and keep LTN and NTN-F quotes."""

from src import data, reporting

reporting.section("01 Data")

data.download_raw_tesouro()
bonds = data.read_bonds()
bonds.to_parquet("data/processed/bonds.parquet", index=False)

reporting.success(
    f"{len(bonds)} quotes on {bonds['quote_date'].nunique()} dates "
    f"({bonds['quote_date'].min().date()} to {bonds['quote_date'].max().date()})"
)
