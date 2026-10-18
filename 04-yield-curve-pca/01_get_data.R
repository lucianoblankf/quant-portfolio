# 01: download the raw Tesouro Direto file (once) and keep the LTN records.

source("R/curve.R")

cli::cli_h1("01 Data")

download_raw_tesouro("data/raw/tesouro_direto.csv")

ltn <- read_ltn("data/raw/tesouro_direto.csv")

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
saveRDS(ltn, "data/processed/ltn.rds")

cli::cli_alert_success(
  "{nrow(ltn)} LTN records on {dplyr::n_distinct(ltn$date)} dates ({min(ltn$date)} to {max(ltn$date)})"
)
