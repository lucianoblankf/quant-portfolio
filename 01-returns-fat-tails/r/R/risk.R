# Risk functions for project 1: returns, moments, normality, VaR and ES.
#
# Conventions: returns are daily log returns (decimals). VaR and ES are POSITIVE
# numbers representing a loss. `alpha` is the confidence level (0.99).

#' Daily log returns of a price vector (one element shorter than the input).
log_returns <- function(prices) {
  diff(log(prices))
}

#' Jarque-Bera normality test, implemented by hand: JB = n / 6 * (S^2 + K^2 / 4),
#' with K the excess kurtosis; chi-squared with 2 degrees of freedom under normality.
jarque_bera <- function(returns) {
  n <- length(returns)
  s <- moments::skewness(returns)
  k <- moments::kurtosis(returns) - 3
  jb <- n / 6 * (s^2 + k^2 / 4)
  tibble::tibble(jarque_bera = jb, jb_p_value = stats::pchisq(jb, df = 2, lower.tail = FALSE))
}

#' Historical-simulation VaR: the empirical (1 - alpha) quantile, sign flipped.
historical_var <- function(returns, alpha = 0.99) {
  -unname(stats::quantile(returns, 1 - alpha, type = 7))
}

#' Parametric (normal) VaR with the sample mean and standard deviation.
parametric_var <- function(returns, alpha = 0.99) {
  -(mean(returns) + stats::sd(returns) * stats::qnorm(1 - alpha))
}

#' Historical expected shortfall: average loss on days at or below the VaR cutoff.
historical_es <- function(returns, alpha = 0.99) {
  cutoff <- stats::quantile(returns, 1 - alpha, type = 7)
  -mean(returns[returns <= cutoff])
}

#' Descriptive statistics and Jarque-Bera test for one return series (one row).
summarise_returns <- function(returns, trading_days = 252) {
  tibble::tibble(
    n = length(returns),
    mean = mean(returns),
    vol = stats::sd(returns),
    ann_vol = stats::sd(returns) * sqrt(trading_days),
    skew = moments::skewness(returns),
    excess_kurtosis = moments::kurtosis(returns) - 3
  ) |>
    dplyr::bind_cols(jarque_bera(returns))
}

#' VaR / ES table for one return series at several confidence levels.
var_table <- function(returns, alphas = c(0.95, 0.99)) {
  purrr::map(alphas, \(alpha) {
    hist_var <- historical_var(returns, alpha)
    param_var <- parametric_var(returns, alpha)
    tibble::tibble(
      confidence = alpha,
      historical_var = hist_var,
      parametric_var = param_var,
      hist_over_param = hist_var / param_var,
      historical_es = historical_es(returns, alpha),
      param_breach_rate = mean(returns < -param_var),
      expected_breach_rate = 1 - alpha
    )
  }) |>
    purrr::list_rbind()
}
