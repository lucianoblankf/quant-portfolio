"""01: download the raw SPY option chain once (needs internet only the first time)."""

from src import data, reporting

reporting.section("01 Data")

try:
    path = data.download_raw_chain()
    chain = data.read_raw_chain()
    reporting.success(
        f"{len(chain)} quotes, spot {chain['spot'].iloc[0]:.2f}, expiry {chain['expiry'].iloc[0].date()} ({path})"
    )
except Exception as exc:  # network or data problem: the smile step is skipped, not the project
    reporting.warn(f"SPY chain not available: {exc}")
