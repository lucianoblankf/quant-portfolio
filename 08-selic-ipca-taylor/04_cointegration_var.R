# 04: Johansen cointegration, VAR, Granger causality and impulse responses.

source("R/var_tools.R")
source("R/tables.R")

set.seed(1)

cli::cli_h1("04 Cointegration and VAR")

dataset <- readRDS("data/processed/dataset.rds")
horizon <- 36

# Johansen trace test for Selic and inflation
johansen <- urca::ca.jo(
  as.data.frame(dataset[c("selic", "ipca12")]), type = "trace", ecdet = "const", K = 3
)
johansen_tbl <- tibble::tibble(
  null = c("r <= 1", "r = 0"),               # urca reports r <= 1 first
  trace = johansen@teststat,
  critical_5pct = johansen@cval[, "5pct"]
)
save_table(johansen_tbl, "johansen", digits = 2)
cli::cli_h2("Johansen trace test (selic, ipca12)")
print(round_numeric(johansen_tbl, 2))

# VAR in levels: gap, ipca12, selic (policy rate last: recursive identification)
y <- as.matrix(dataset[c("gap", "ipca12", "selic")])
lag_table <- var_select(y, 8)
p <- lag_table$p[which.min(lag_table$bic)]
fit <- var_fit(y, p)
save_table(lag_table, "var_lag_selection", digits = 3)
cli::cli_alert_info("VAR({p}) selected by BIC, {fit$n_obs} observations")

granger_pairs <- tibble::tribble(
  ~from, ~to,
  "selic", "ipca12",
  "ipca12", "selic",
  "gap", "selic",
  "selic", "gap",
  "gap", "ipca12",
  "ipca12", "gap"
)
granger_tbl <- purrr::map2(granger_pairs$from, granger_pairs$to, \(from, to) granger(fit, from, to)) |>
  purrr::list_rbind()
save_table(granger_tbl, "granger", digits = 4)
cli::cli_h2("Granger causality (F tests)")
print(round_numeric(granger_tbl, 4))

irf <- var_irf_boot(fit, "selic", horizon = horizon, n_boot = 300)
irf_table <- dplyr::bind_rows(
  irf_tidy(irf, "ipca12", fit$names, "IPCA 12m (p.p.)"),
  irf_tidy(irf, "gap", fit$names, "Output gap (% of trend)")
)
save_table(irf_table, "irf_selic_shock", digits = 4)

ipca_irf <- dplyr::filter(irf_table, variable == "IPCA 12m (p.p.)")
peak <- dplyr::slice_max(ipca_irf, abs(response), n = 1)
cli::cli_alert_info(
  "IPCA response to a 1 s.d. Selic shock ({round(sqrt(fit$sigma[3, 3]), 2)} p.p.): peak {round(peak$response, 3)} at month {peak$horizon}, 90% band [{round(peak$lo, 3)}, {round(peak$hi, 3)}]"
)
gap_peak <- irf_table |>
  dplyr::filter(variable == "Output gap (% of trend)") |>
  dplyr::slice_max(abs(response), n = 1)
cli::cli_alert_info("Output gap response: peak {round(gap_peak$response, 3)} at month {gap_peak$horizon}")

# Robustness: add the exchange rate (a forward-looking price) to the VAR
y_fx <- cbind(
  gap = dataset$gap, lfx = 100 * log(dataset$fx), ipca12 = dataset$ipca12, selic = dataset$selic
)
p_fx <- var_select(y_fx, 8) |>
  dplyr::slice_min(bic, n = 1) |>
  dplyr::pull(p)
fit_fx <- var_fit(y_fx, p_fx)
irf_fx <- var_irf_boot(fit_fx, "selic", horizon = horizon, n_boot = 300)
ipca_fx <- irf_tidy(irf_fx, "ipca12", fit_fx$names, "IPCA 12m, VAR with FX")
save_table(ipca_fx, "irf_ipca_with_fx", digits = 4)

peak_fx <- dplyr::slice_max(ipca_fx, abs(response), n = 1)
at_24 <- \(tbl) dplyr::filter(tbl, horizon == 24)
cli::cli_alert_info(
  "VAR({p_fx}) with FX: peak {round(peak_fx$response, 3)} at month {peak_fx$horizon}; month 24: {round(at_24(ipca_fx)$response, 3)} [{round(at_24(ipca_fx)$lo, 3)}, {round(at_24(ipca_fx)$hi, 3)}]"
)
cli::cli_alert_info(
  "Baseline VAR month 24: {round(at_24(ipca_irf)$response, 3)} [{round(at_24(ipca_irf)$lo, 3)}, {round(at_24(ipca_irf)$hi, 3)}]"
)
