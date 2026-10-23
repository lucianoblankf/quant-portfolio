"""01: raw OHLC prices (downloaded once) and the feature / target dataset."""

from src import config, data, reporting, volml

reporting.section("01 Data")

data.download_raw_ohlc()
ohlc, fx = data.read_ohlc()
dataset = volml.make_dataset(ohlc, fx, h=config.HORIZON)
dataset.to_parquet("data/processed/dataset.parquet")

features = [c for c in dataset if c.startswith("f_")]
reporting.success(
    f"{len(dataset)} days, {dataset.index.min().date()} to {dataset.index.max().date()}; {len(features)} features"
)
reporting.info(", ".join(features))
