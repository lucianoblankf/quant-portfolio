# Taylor rule estimation with HAC standard errors, long-run coefficients and sub-samples.

#' Newey-West (HAC) covariance matrix used throughout.
hac_vcov <- function(model, lag = 6) {
  sandwich::NeweyWest(model, lag = lag, prewhite = FALSE)
}

#' Coefficient table with HAC standard errors (tidy).
tidy_hac <- function(model, lag = 6) {
  lmtest::coeftest(model, vcov. = hac_vcov(model, lag)) |>
    broom::tidy()
}

#' Unit-root tests: ADF (H0 unit root) and KPSS (H0 stationary) p-values for a series.
unit_root_tests <- function(x, name) {
  tibble::tibble(
    series = name,
    adf_p = suppressWarnings(tseries::adf.test(x)$p.value),
    kpss_p = suppressWarnings(tseries::kpss.test(x)$p.value)
  )
}

#' Short- and long-run Taylor-rule coefficients on a sub-sample (one row).
taylor_subsample <- function(data, label) {
  m <- stats::lm(selic ~ ipca12 + gap + selic_l1, data = data)
  cf <- stats::coef(m)
  tibble::tibble(
    period = label,
    n = nrow(data),
    infl_sr = cf[["ipca12"]],
    gap_sr = cf[["gap"]],
    rho = cf[["selic_l1"]],
    infl_lr = cf[["ipca12"]] / (1 - cf[["selic_l1"]]),
    r2 = summary(m)$r.squared
  )
}
