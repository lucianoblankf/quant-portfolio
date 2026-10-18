# 03: PCA of weekly yield changes, sub-period stability, stress scenarios, reconstruction.

source("R/pca.R")
source("R/tables.R")

cli::cli_h1("03 PCA")

curve <- readRDS("data/processed/curve.rds")
tenors <- c(1, 2, 3, 5)

changes <- weekly_changes(curve)
cli::cli_alert_info("{nrow(changes)} weekly changes")

fit <- yield_pca(changes)

variance <- variance_table(fit)
loadings <- loadings_table(fit)
correlations <- factor_correlations(fit, changes)
subperiods <- subperiod_table(changes)
stress <- pc_stress(fit, last_yields = unlist(utils::tail(curve[-1], 1)), tenors = tenors)
reconstruction <- reconstruction_rmse(fit, changes)

purrr::walk2(
  list(variance, loadings, correlations, subperiods, stress, reconstruction),
  c("variance_explained", "loadings", "factor_correlations", "subperiods", "pc_stress", "reconstruction_rmse"),
  \(tbl, name) save_table(tbl, name, digits = 3)
)
saveRDS(fit, "data/processed/pca_fit.rds")

cli::cli_h2("Variance explained")
print(round_numeric(variance, 4))
cli::cli_h2("Loadings")
print(round_numeric(loadings, 3))
cli::cli_h2("PC scores vs simple factors")
print(round_numeric(correlations, 3))
cli::cli_h2("By sub-period")
print(round_numeric(subperiods, 3), width = Inf)
cli::cli_h2("Stress scenarios (+/- 3 sd), return of a zero-coupon bond at each tenor")
print(
  stress |>
    dplyr::select(-shift_bp) |>
    tidyr::pivot_wider(names_from = tenor, values_from = return_pct, names_prefix = "ret_") |>
    round_numeric(2)
)
cli::cli_h2("Reconstruction error")
print(round_numeric(reconstruction, 2))
