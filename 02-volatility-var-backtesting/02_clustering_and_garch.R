# 02: evidence of volatility clustering and full-sample GARCH(1,1) fits.

source("R/garch.R")
source("R/tables.R")

cli::cli_h1("02 Clustering and GARCH fits")

returns <- readRDS("data/processed/returns.rds")
r <- returns$log_return

# Ljung-Box on returns and squared returns
lb <- tibble::tibble(
  series = c("returns", "squared_returns"),
  p_value = c(
    stats::Box.test(r, lag = 10, type = "Ljung-Box")$p.value,
    stats::Box.test(r^2, lag = 10, type = "Ljung-Box")$p.value
  )
)
save_table(lb, "ljung_box")
cli::cli_alert_info(
  "Ljung-Box (10 lags): returns p = {signif(lb$p_value[1], 3)}, squared returns p = {signif(lb$p_value[2], 3)}"
)

# Full-sample GARCH(1,1), normal and Student-t errors
garch_fits <- dplyr::bind_rows(
  tidy_garch_fit(fit_garch(r, "norm"), "normal"),
  tidy_garch_fit(fit_garch(r, "std"), "student_t")
)
save_table(garch_fits, "garch_fit", digits = 6)

cli::cli_h2("Full-sample GARCH(1,1)")
print(garch_fits, width = Inf)
