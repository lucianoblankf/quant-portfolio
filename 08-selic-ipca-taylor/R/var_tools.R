# Small VAR toolkit (OLS, lag selection, Granger, orthogonalised IRF with bootstrap bands).
# Written from scratch so the project does not depend on the `vars` package.

#' Regressor matrix for a VAR(p) with constant. `data` is a T x k matrix.
var_design <- function(data, p) {
  n <- nrow(data)
  lags <- purrr::map(seq_len(p), \(l) data[(p - l + 1):(n - l), , drop = FALSE])
  list(
    y = data[(p + 1):n, , drop = FALSE],
    z = cbind(1, do.call(cbind, lags))
  )
}

#' OLS estimation of a VAR(p).
var_fit <- function(data, p) {
  d <- var_design(data, p)
  coefs <- solve(crossprod(d$z), crossprod(d$z, d$y))   # (1 + k p) x k
  resid <- d$y - d$z %*% coefs
  list(
    coefs = coefs, resid = resid,
    sigma = crossprod(resid) / (nrow(resid) - ncol(d$z)),
    p = p, k = ncol(data), n_obs = nrow(resid), data = data, names = colnames(data)
  )
}

#' Lag selection by information criteria on a common sample.
var_select <- function(data, max_lag = 8) {
  n <- nrow(data)
  k <- ncol(data)
  purrr::map(seq_len(max_lag), \(p) {
    d <- var_design(data[(max_lag - p + 1):n, , drop = FALSE], p)
    coefs <- solve(crossprod(d$z), crossprod(d$z, d$y))
    resid <- d$y - d$z %*% coefs
    n_obs <- nrow(resid)
    sigma_ml <- crossprod(resid) / n_obs
    n_par <- k * (1 + k * p)
    tibble::tibble(
      p = p,
      aic = log(det(sigma_ml)) + 2 * n_par / n_obs,
      bic = log(det(sigma_ml)) + log(n_obs) * n_par / n_obs
    )
  }) |>
    purrr::list_rbind()
}

#' Granger causality: do the lags of `from` help predict `to`? Wald (F) test on those
#' coefficients in the equation of `to`.
granger <- function(fit, from, to) {
  from_i <- match(from, fit$names)
  to_i <- match(to, fit$names)
  rows <- 1 + (0:(fit$p - 1)) * fit$k + from_i      # rows of the coefficients on lags of `from`
  d <- var_design(fit$data, fit$p)
  y <- d$y[, to_i]
  rss <- function(z) sum(stats::residuals(stats::lm.fit(z, y))^2)
  q <- length(rows)
  df2 <- nrow(d$z) - ncol(d$z)
  f_stat <- ((rss(d$z[, -rows, drop = FALSE]) - rss(d$z)) / q) / (rss(d$z) / df2)
  tibble::tibble(
    test = paste(from, "->", to),
    f_stat = f_stat,
    p_value = stats::pf(f_stat, q, df2, lower.tail = FALSE)
  )
}

#' MA coefficients Phi_0 .. Phi_H of a fitted VAR.
var_ma <- function(coefs, k, p, horizon) {
  a <- purrr::map(seq_len(p), \(l) t(coefs[1 + (l - 1) * k + seq_len(k), , drop = FALSE]))
  phi <- vector("list", horizon + 1)
  phi[[1]] <- diag(k)
  for (h in seq_len(horizon)) {
    total <- matrix(0, k, k)
    for (l in seq_len(min(h, p))) {
      total <- total + a[[l]] %*% phi[[h - l + 1]]
    }
    phi[[h + 1]] <- total
  }
  phi
}

#' Orthogonalised (Cholesky) IRF of every variable to a one-s.d. shock in `shock`.
#' The ordering of the columns is the identification: earlier variables can affect later
#' ones contemporaneously, not the reverse. Returns a (horizon + 1) x k matrix.
var_irf <- function(fit, shock, horizon = 36) {
  chol_factor <- t(chol(fit$sigma))
  phi <- var_ma(fit$coefs, fit$k, fit$p, horizon)
  shock_i <- match(shock, fit$names)
  t(vapply(phi, \(m) (m %*% chol_factor)[, shock_i], numeric(fit$k)))
}

#' Residual-bootstrap bands for the IRF. Returns a list of three (horizon + 1) x k
#' matrices: point, lo, hi.
var_irf_boot <- function(fit, shock, horizon = 36, n_boot = 300, level = 0.90, seed = 1) {
  set.seed(seed)
  n <- nrow(fit$data)
  k <- fit$k
  p <- fit$p
  centred <- scale(fit$resid, scale = FALSE)
  draws <- array(NA_real_, c(horizon + 1, k, n_boot))

  for (b in seq_len(n_boot)) {
    shocks <- centred[sample(nrow(centred), replace = TRUE), , drop = FALSE]
    sim <- fit$data
    for (t in (p + 1):n) {
      z <- c(1, as.vector(t(sim[(t - 1):(t - p), , drop = FALSE])))
      sim[t, ] <- z %*% fit$coefs + shocks[t - p, ]
    }
    draws[, , b] <- var_irf(var_fit(sim, p), shock, horizon)
  }

  tail_prob <- (1 - level) / 2
  list(
    point = var_irf(fit, shock, horizon),
    lo = apply(draws, c(1, 2), stats::quantile, tail_prob, na.rm = TRUE),
    hi = apply(draws, c(1, 2), stats::quantile, 1 - tail_prob, na.rm = TRUE)
  )
}

#' IRF of one variable as a tidy table: horizon, response, lo, hi.
irf_tidy <- function(irf, variable, names, label = variable) {
  j <- match(variable, names)
  tibble::tibble(
    horizon = seq_len(nrow(irf$point)) - 1,
    response = irf$point[, j], lo = irf$lo[, j], hi = irf$hi[, j],
    variable = label
  )
}

#' Hodrick-Prescott trend (two-sided), via the closed-form linear solve.
hp_trend <- function(y, lambda = 14400) {
  n <- length(y)
  d <- diff(diag(n), differences = 2)
  as.numeric(solve(diag(n) + lambda * crossprod(d), y))
}
