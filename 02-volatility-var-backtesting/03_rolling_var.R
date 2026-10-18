# 03: rolling out-of-sample VaR forecasts (1,000-day window, refit every 21 days).
# The result is cached; delete data/processed/rolling_var.rds to recompute.

source("R/garch.R")
source("R/var_models.R")

cli::cli_h1("03 Rolling VaR")

cache <- "data/processed/rolling_var.rds"

if (file.exists(cache)) {
  cli::cli_alert_info("Using cached forecasts: {.path {cache}}")
} else {
  returns <- readRDS("data/processed/returns.rds")
  cli::cli_alert_info("Estimating (this is the slow part)")
  rolling <- rolling_var(returns$date, returns$log_return)
  saveRDS(rolling, cache)
}

rolling <- readRDS(cache)
cli::cli_alert_success(
  "{dplyr::n_distinct(rolling$date)} out-of-sample days, {min(rolling$date)} to {max(rolling$date)}"
)
