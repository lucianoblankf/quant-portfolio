# 02: constant-maturity zero curve (1, 2, 3 and 5 years) from the individual LTN bonds.

source("R/curve.R")

cli::cli_h1("02 Constant-maturity curve")

ltn <- readRDS("data/processed/ltn.rds")
tenors <- c(1, 2, 3, 5)

curve <- build_constant_maturity_curve(ltn, tenors)
saveRDS(curve, "data/processed/curve.rds")

cli::cli_alert_success(
  "Curve built on {nrow(curve)} of {dplyr::n_distinct(ltn$date)} dates ({min(curve$date)} to {max(curve$date)})"
)
cli::cli_alert_info(
  "A 5-year point needs a bond beyond five years, so some years have gaps (none in 2021)"
)
