# GARCH(1,1) and EWMA volatility models, written from scratch (no rugarch).
#
# Conventions: returns are daily log returns (decimals).

#' Conditional variance path of a GARCH(1,1):
#' sigma2_t = omega + alpha * r_{t-1}^2 + beta * sigma2_{t-1}, with sigma2_1 = var(r).
#' The recursion is linear in sigma2, so it is computed with a recursive filter.
garch_filter <- function(par, returns) {
  omega <- par[1]
  alpha <- par[2]
  beta <- par[3]
  n <- length(returns)
  x <- c(stats::var(returns), omega + alpha * returns[-n]^2)
  as.numeric(stats::filter(x, beta, method = "recursive"))
}

#' Negative log-likelihood of a GARCH(1,1). `dist` is "norm" or "std"
#' (Student-t scaled to unit variance, with `par[4]` degrees of freedom).
garch_nll <- function(par, returns, dist = "norm") {
  omega <- par[1]
  alpha <- par[2]
  beta <- par[3]
  if (omega <= 0 || alpha < 0 || beta < 0 || alpha + beta >= 0.9999) {
    return(1e10)
  }
  sigma2 <- garch_filter(par[1:3], returns)
  z <- returns / sqrt(sigma2)
  if (dist == "norm") {
    ll <- -0.5 * (log(2 * pi) + log(sigma2) + z^2)
  } else {
    nu <- par[4]
    if (nu <= 2.05) {
      return(1e10)
    }
    ll <- lgamma((nu + 1) / 2) - lgamma(nu / 2) - 0.5 * log(pi * (nu - 2)) -
      0.5 * log(sigma2) - (nu + 1) / 2 * log(1 + z^2 / (nu - 2))
  }
  -sum(ll)
}

#' Maximum likelihood fit of a GARCH(1,1). Returns are scaled to percent inside the
#' optimiser for numerical stability and omega is rescaled back afterwards.
fit_garch <- function(returns, dist = "norm") {
  scale_factor <- 100
  scaled <- returns * scale_factor
  v <- stats::var(scaled)

  start <- c(omega = 0.05 * v, alpha = 0.08, beta = 0.90)
  lower <- c(1e-8, 1e-6, 1e-6)
  upper <- c(10 * v, 0.5, 0.9998)
  if (dist == "std") {
    start <- c(start, nu = 8)
    lower <- c(lower, 2.1)
    upper <- c(upper, 60)
  }

  opt <- stats::optim(
    start, garch_nll,
    returns = scaled, dist = dist, method = "L-BFGS-B", lower = lower, upper = upper
  )
  par <- opt$par
  par[1] <- par[1] / scale_factor^2
  list(par = par, loglik = -opt$value, dist = dist, convergence = opt$convergence)
}

#' One-step-ahead variance forecast from the end of the sample.
garch_forecast_var <- function(fit, returns) {
  sigma2 <- garch_filter(fit$par[1:3], returns)
  fit$par[1] + fit$par[2] * utils::tail(returns, 1)^2 + fit$par[3] * utils::tail(sigma2, 1)
}

#' EWMA (RiskMetrics) one-step-ahead variance forecast, zero mean.
ewma_forecast_var <- function(returns, lambda = 0.94) {
  sigma2 <- stats::var(returns[1:30])
  for (x in returns[-(1:30)]) {
    sigma2 <- lambda * sigma2 + (1 - lambda) * x^2
  }
  sigma2
}

#' Tidy summary of a GARCH fit (one row): parameters, persistence, half-life, AIC.
tidy_garch_fit <- function(fit, label) {
  p <- fit$par
  k <- length(p)
  tibble::tibble(
    dist = label,
    omega = p[[1]],
    alpha = p[[2]],
    beta = p[[3]],
    persistence = p[[2]] + p[[3]],
    nu = if (k == 4) p[[4]] else NA_real_,
    half_life_days = log(0.5) / log(p[[2]] + p[[3]]),
    loglik = fit$loglik,
    aic = 2 * k - 2 * fit$loglik
  )
}
