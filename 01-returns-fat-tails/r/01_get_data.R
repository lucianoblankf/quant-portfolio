# 01: download the raw prices (once) and build the processed log returns.

source("R/data.R")
source("R/risk.R")

cli::cli_h1("01 Data")

download_raw_prices("data/raw/prices.csv")

prices <- read_raw_prices("data/raw/prices.csv")

# One row per asset and date; each asset's returns use only its own non-missing prices.
returns <- prices |>
  tidyr::pivot_longer(-date, names_to = "asset", values_to = "price") |>
  tidyr::drop_na(price) |>
  dplyr::arrange(asset, date) |>
  dplyr::group_by(asset) |>
  dplyr::mutate(log_return = c(NA_real_, log_returns(price))) |>
  dplyr::ungroup() |>
  tidyr::drop_na(log_return)

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
saveRDS(returns, "data/processed/returns.rds")

cli::cli_alert_success(
  "{nrow(returns)} returns saved ({min(returns$date)} to {max(returns$date)})"
)
