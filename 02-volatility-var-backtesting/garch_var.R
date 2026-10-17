# Volatility models and VaR backtesting functions for project 2.
# Everything is written from scratch (no rugarch): EWMA, GARCH(1,1) by maximum
# likelihood, rolling VaR forecasts, and the Kupiec / Christoffersen tests.
#
# Conventions: returns are daily log returns (decimals); VaR is a POSITIVE loss.

# ---- GARCH(1,1) --------------------------------------------------------------
# sigma2_t = omega + alpha * r_{t-1}^2 + beta * sigma2_{t-1}
garch_filter <- function(par, r) {
  omega <- par[1]; alpha <- par[2]; beta <- par[3]
  n <- length(r)
  x <- c(var(r), omega + alpha * r[-n]^2)   # x[1] is the starting variance
  as.numeric(stats::filter(x, beta, method = "recursive"))
}

# Negative log-likelihood. dist = "norm" or "std" (Student-t with unit variance).
garch_nll <- function(par, r, dist = "norm") {
  omega <- par[1]; alpha <- par[2]; beta <- par[3]
  if (omega <= 0 || alpha < 0 || beta < 0 || alpha + beta >= 0.9999) return(1e10)
  s2 <- garch_filter(par[1:3], r)
  z <- r / sqrt(s2)
  if (dist == "norm") {
    ll <- -0.5 * (log(2 * pi) + log(s2) + z^2)
  } else {
    nu <- par[4]
    if (nu <= 2.05) return(1e10)
    ll <- lgamma((nu + 1) / 2) - lgamma(nu / 2) - 0.5 * log(pi * (nu - 2)) -
      0.5 * log(s2) - (nu + 1) / 2 * log(1 + z^2 / (nu - 2))
  }
  -sum(ll)
}

fit_garch <- function(r, dist = "norm") {
  v <- var(r)
  start <- c(omega = 0.05 * v, alpha = 0.08, beta = 0.90)
  lower <- c(1e-12, 1e-6, 1e-6); upper <- c(10 * v, 0.5, 0.9998)
  if (dist == "std") { start <- c(start, nu = 8); lower <- c(lower, 2.1); upper <- c(upper, 60) }
  # Scale returns to percent for numerical stability of the optimiser.
  scale <- 100
  rs <- r * scale
  st <- start; st[1] <- st[1] * scale^2
  lo <- lower; lo[1] <- 1e-8; up <- upper; up[1] <- 10 * var(rs)
  opt <- optim(st, garch_nll, r = rs, dist = dist, method = "L-BFGS-B", lower = lo, upper = up)
  p <- opt$par; p[1] <- p[1] / scale^2
  list(par = p, loglik = -opt$value, dist = dist, convergence = opt$convergence)
}

# One-step-ahead variance forecast from the end of the sample.
garch_forecast_var <- function(fit, r) {
  s2 <- garch_filter(fit$par[1:3], r)
  fit$par[1] + fit$par[2] * tail(r, 1)^2 + fit$par[3] * tail(s2, 1)
}

# ---- EWMA (RiskMetrics) --------------------------------------------------------
ewma_forecast_var <- function(r, lambda = 0.94) {
  s2 <- var(r[1:30])
  for (x in r[-(1:30)]) s2 <- lambda * s2 + (1 - lambda) * x^2
  s2
}

# VaR from a sigma forecast: -(mu + sigma * q), q the (1-alpha) quantile of the
# standardised distribution. Mean is set to zero for the volatility models.
var_from_sigma <- function(sigma, alpha, dist = "norm", nu = NULL) {
  q <- if (dist == "norm") qnorm(1 - alpha) else qt(1 - alpha, nu) * sqrt((nu - 2) / nu)
  -sigma * q
}

# ---- rolling forecasts -----------------------------------------------------------
# For each day t in the test window, forecast VaR using only returns before t.
# GARCH parameters are re-estimated every `refit` days on a rolling window.
rolling_var <- function(r, alphas = c(0.95, 0.99), window = 1000, refit = 21,
                        hist_window = 250, lambda = 0.94) {
  n <- length(r); idx <- (window + 1):n
  out <- vector("list", length(idx)); fit_n <- NULL; fit_t <- NULL
  for (k in seq_along(idx)) {
    t <- idx[k]; past <- r[(t - window):(t - 1)]
    if ((k - 1) %% refit == 0) { fit_n <- fit_garch(past, "norm"); fit_t <- fit_garch(past, "std") }
    s_n <- sqrt(garch_forecast_var(fit_n, past))
    s_t <- sqrt(garch_forecast_var(fit_t, past))
    s_e <- sqrt(ewma_forecast_var(past, lambda))
    h   <- tail(past, hist_window)
    row <- list(index = t, ret = r[t])
    for (a in alphas) {
      tag <- sprintf("%02d", round(100 * a))
      row[[paste0("hist_", tag)]]  <- -quantile(h, 1 - a, names = FALSE)
      row[[paste0("norm_", tag)]]  <- var_from_sigma(sqrt(var(h)), a)
      row[[paste0("ewma_", tag)]]  <- var_from_sigma(s_e, a)
      row[[paste0("garch_", tag)]] <- var_from_sigma(s_n, a)
      row[[paste0("garcht_", tag)]] <- var_from_sigma(s_t, a, "std", fit_t$par[4])
    }
    out[[k]] <- as.data.frame(row)
  }
  do.call(rbind, out)
}

# ---- backtests -----------------------------------------------------------------
# hits: 0/1 vector of VaR breaches; p: expected breach probability (1 - alpha).
kupiec_pof <- function(hits, p) {
  n <- length(hits); x <- sum(hits)
  ll0 <- (n - x) * log(1 - p) + x * log(p)
  phat <- x / n
  ll1 <- ifelse(x == 0, n * log(1 - phat), ifelse(x == n, n * log(phat),
          (n - x) * log(1 - phat) + x * log(phat)))
  lr <- -2 * (ll0 - ll1)
  c(breaches = x, rate = phat, LR = lr, p_value = pchisq(lr, 1, lower.tail = FALSE))
}

christoffersen_ind <- function(hits) {
  h <- as.integer(hits); a <- h[-length(h)]; b <- h[-1]
  n00 <- sum(a == 0 & b == 0); n01 <- sum(a == 0 & b == 1)
  n10 <- sum(a == 1 & b == 0); n11 <- sum(a == 1 & b == 1)
  pi01 <- n01 / (n00 + n01); pi11 <- ifelse(n10 + n11 == 0, 0, n11 / (n10 + n11))
  pi   <- (n01 + n11) / (n00 + n01 + n10 + n11)
  lg <- function(x, p) ifelse(x == 0, 0, x * log(p))
  ll0 <- lg(n00 + n10, 1 - pi) + lg(n01 + n11, pi)
  ll1 <- lg(n00, 1 - pi01) + lg(n01, pi01) + lg(n10, 1 - pi11) + lg(n11, pi11)
  lr <- -2 * (ll0 - ll1)
  c(LR = lr, p_value = pchisq(lr, 1, lower.tail = FALSE))
}

backtest_table <- function(df, models, alpha) {
  tag <- sprintf("%02d", round(100 * alpha)); p <- 1 - alpha
  do.call(rbind, lapply(models, function(m) {
    hits <- as.integer(df$ret < -df[[paste0(m, "_", tag)]])
    k <- kupiec_pof(hits, p); ci <- christoffersen_ind(hits)
    cc <- k[["LR"]] + ci[["LR"]]
    data.frame(model = m, confidence = alpha, n = length(hits), breaches = k[["breaches"]],
               expected = round(length(hits) * p, 1), rate = k[["rate"]],
               kupiec_p = k[["p_value"]], indep_p = ci[["p_value"]],
               cond_cov_p = pchisq(cc, 2, lower.tail = FALSE))
  }))
}

# Basel traffic light for 250 days of 99% VaR: green <= 4, yellow 5-9, red >= 10.
basel_zone <- function(breaches) ifelse(breaches <= 4, "green", ifelse(breaches <= 9, "yellow", "red"))
