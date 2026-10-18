# VaR forecasts from volatility models and the rolling out-of-sample engine.
# VaR is a POSITIVE loss.

#' VaR from a sigma forecast: -sigma * q, with q the (1 - alpha) quantile of the
#' standardised distribution (normal, or Student-t scaled to unit variance).
var_from_sigma <- function(sigma, alpha, dist = "norm", nu = NULL) {
  q <- if (dist == "norm") {
    stats::qnorm(1 - alpha)
  } else {
    stats::qt(1 - alpha, nu) * sqrt((nu - 2) / nu)
  }
  -sigma * q
}

#' Rolling one-day-ahead VaR forecasts, using only returns before each day.
#' GARCH parameters are re-estimated every `refit` days on a rolling `window`.
#' Models: hist (empirical quantile), norm (sample sigma), ewma, garch (normal), garcht
#' (Student-t). Returns a long tibble: date, ret, model, confidence, var; plus the daily
#' GARCH-t conditional sigma in an attribute-free second table (`sigma_garcht`).
rolling_var <- function(dates, returns, alphas = c(0.95, 0.99), window = 1000, refit = 21,
                        hist_window = 250, lambda = 0.94) {
  n <- length(returns)
  idx <- (window + 1):n
  fit_norm <- NULL
  fit_t <- NULL

  rows <- vector("list", length(idx))
  for (k in seq_along(idx)) {
    t <- idx[k]
    past <- returns[(t - window):(t - 1)]
    if ((k - 1) %% refit == 0) {
      fit_norm <- fit_garch(past, "norm")
      fit_t <- fit_garch(past, "std")
    }
    sigma_norm <- sqrt(garch_forecast_var(fit_norm, past))
    sigma_t <- sqrt(garch_forecast_var(fit_t, past))
    sigma_ewma <- sqrt(ewma_forecast_var(past, lambda))
    recent <- utils::tail(past, hist_window)

    rows[[k]] <- purrr::map(alphas, \(alpha) {
      tibble::tibble(
        date = dates[t], ret = returns[t], confidence = alpha,
        model = c("hist", "norm", "ewma", "garch", "garcht"),
        var = c(
          -stats::quantile(recent, 1 - alpha, names = FALSE),
          var_from_sigma(stats::sd(recent), alpha),
          var_from_sigma(sigma_ewma, alpha),
          var_from_sigma(sigma_norm, alpha),
          var_from_sigma(sigma_t, alpha, "std", fit_t$par[[4]])
        ),
        sigma_garcht = sigma_t
      )
    }) |>
      purrr::list_rbind()
  }
  purrr::list_rbind(rows)
}

#' Display names of the VaR models.
model_labels <- function() {
  c(
    hist = "Historical (250d)", norm = "Normal (250d)", ewma = "EWMA 0.94",
    garch = "GARCH-normal", garcht = "GARCH-t"
  )
}
