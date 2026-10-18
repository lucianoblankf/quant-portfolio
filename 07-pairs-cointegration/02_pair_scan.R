# 02: scan every pair in the formation window, select pairs, check out-of-sample stability.

source("R/pairs.R")
source("R/tables.R")

cli::cli_h1("02 Pair scan")

config <- pairs_config()
prices <- readRDS("data/processed/prices.rds")

log_prices <- prices |>
  dplyr::mutate(dplyr::across(-date, log))
formation <- log_prices |> dplyr::filter(date < config$formation_end)
trading <- log_prices |> dplyr::filter(date >= config$formation_end)

formation_matrix <- as.matrix(formation[-1])
trading_matrix <- as.matrix(trading[-1])

scan <- scan_pairs(formation_matrix)
save_table(scan, "formation_scan")

n_pass <- sum(scan$adf < config$adf_cv_5pct)
cli::cli_alert_info(
  "Formation window: {nrow(scan)} pairs, {n_pass} cointegrated at 5% (expected by chance: about {round(0.05 * nrow(scan))})"
)
cli::cli_h2("Top 8 pairs by Engle-Granger ADF (more negative = stronger)")
print(round_numeric(utils::head(scan, 8), 3))

selected <- scan |>
  dplyr::filter(adf < config$adf_cv_5pct, dplyr::between(half_life, config$half_life_range[1], config$half_life_range[2])) |>
  utils::head(config$n_selected)
saveRDS(selected, "data/processed/selected_pairs.rds")
cli::cli_alert_success("Selected {nrow(selected)} pairs")

# Out-of-sample stability: spread with the formation beta, and re-estimation on the trading window
stability <- selected |>
  purrr::pmap(\(y, x, beta, adf, half_life, ...) {
    y_new <- trading_matrix[, y]
    x_new <- trading_matrix[, x]
    refit <- engle_granger(y_new, x_new)
    tibble::tibble(
      pair = paste(toupper(y), toupper(x), sep = "/"),
      form_adf = adf,
      form_half_life = half_life,
      oos_adf_fixed_beta = suppressWarnings(tseries::adf.test(y_new - beta * x_new, k = 1)$statistic[[1]]),
      oos_adf_refit = refit$adf,
      form_beta = beta,
      oos_beta = refit$beta
    )
  }) |>
  purrr::list_rbind()
save_table(stability, "oos_stability")
cli::cli_h2("Out-of-sample stability of the selected pairs")
print(round_numeric(stability, 3), width = Inf)
