# Small VAR toolkit (OLS, lag selection, Granger, orthogonalised IRF with bootstrap bands).
# Written from scratch so the project does not depend on the `vars` package.

# Build the regressor matrix for a VAR(p) with constant. Y is T x k.
var_design <- function(Y, p) {
  n <- nrow(Y); k <- ncol(Y)
  Z <- cbind(1, do.call(cbind, lapply(1:p, function(l) Y[(p - l + 1):(n - l), , drop = FALSE])))
  list(Y = Y[(p + 1):n, , drop = FALSE], Z = Z)
}

var_fit <- function(Y, p) {
  d <- var_design(Y, p)
  B <- solve(crossprod(d$Z), crossprod(d$Z, d$Y))             # (1 + k p) x k
  U <- d$Y - d$Z %*% B
  T <- nrow(U); k <- ncol(Y)
  Sigma <- crossprod(U) / (T - ncol(d$Z))
  list(B = B, U = U, Sigma = Sigma, p = p, k = k, T = T, Y = Y, names = colnames(Y))
}

# Lag selection by information criteria on a common sample.
var_select <- function(Y, pmax = 8) {
  n <- nrow(Y); k <- ncol(Y)
  do.call(rbind, lapply(1:pmax, function(p) {
    d <- var_design(Y[(pmax - p + 1):n, , drop = FALSE], p)
    B <- solve(crossprod(d$Z), crossprod(d$Z, d$Y)); U <- d$Y - d$Z %*% B
    T <- nrow(U); S <- crossprod(U) / T; npar <- k * (1 + k * p)
    data.frame(p = p, AIC = log(det(S)) + 2 * npar / T, BIC = log(det(S)) + log(T) * npar / T)
  }))
}

# Granger causality: do lags of `from` help predict `to`? Wald (F) test on those coefficients.
granger <- function(fit, from, to) {
  fi <- match(from, fit$names); ti <- match(to, fit$names)
  idx <- 1 + (0:(fit$p - 1)) * fit$k + fi                      # rows of B for lags of `from`
  d <- var_design(fit$Y, fit$p)
  y <- d$Y[, ti]; Zu <- d$Z; Zr <- d$Z[, -idx, drop = FALSE]
  rss <- function(Z) sum(residuals(lm.fit(Z, y))^2)
  q <- length(idx); df2 <- nrow(Zu) - ncol(Zu)
  F <- ((rss(Zr) - rss(Zu)) / q) / (rss(Zu) / df2)
  c(F = F, p_value = pf(F, q, df2, lower.tail = FALSE))
}

# Companion-form MA coefficients Phi_0..Phi_H.
var_ma <- function(B, k, p, H) {
  A <- lapply(1:p, function(l) t(B[1 + (l - 1) * k + 1:k, , drop = FALSE]))   # k x k each
  Phi <- vector("list", H + 1); Phi[[1]] <- diag(k)
  for (h in 1:H) {
    s <- matrix(0, k, k)
    for (l in 1:min(h, p)) s <- s + A[[l]] %*% Phi[[h - l + 1]]
    Phi[[h + 1]] <- s
  }
  Phi
}

# Orthogonalised (Cholesky) IRF of every variable to a one-s.d. shock in `shock`.
# Variable ordering in Y is the identification: earlier variables can affect later ones
# contemporaneously, not the reverse.
var_irf <- function(fit, shock, H = 36) {
  P <- t(chol(fit$Sigma)); Phi <- var_ma(fit$B, fit$k, fit$p, H)
  si <- match(shock, fit$names)
  t(sapply(Phi, function(M) (M %*% P)[, si]))                   # (H+1) x k
}

# Residual-bootstrap bands for the IRF.
var_irf_boot <- function(fit, shock, H = 36, R = 300, level = 0.90, seed = 1) {
  set.seed(seed)
  n <- nrow(fit$Y); k <- fit$k; p <- fit$p
  Uc <- scale(fit$U, scale = FALSE)
  draws <- array(NA_real_, c(H + 1, k, R))
  for (r in 1:R) {
    Ub <- Uc[sample(nrow(Uc), replace = TRUE), , drop = FALSE]
    Yb <- fit$Y;
    for (t in (p + 1):n) {
      z <- c(1, as.vector(t(Yb[(t - 1):(t - p), , drop = FALSE])))
      Yb[t, ] <- z %*% fit$B + Ub[t - p, ]
    }
    draws[, , r] <- var_irf(var_fit(Yb, p), shock, H)
  }
  a <- (1 - level) / 2
  list(point = var_irf(fit, shock, H),
       lo = apply(draws, c(1, 2), quantile, a, na.rm = TRUE),
       hi = apply(draws, c(1, 2), quantile, 1 - a, na.rm = TRUE))
}

# Hodrick-Prescott trend (two-sided), via the closed-form linear solve.
hp_trend <- function(y, lambda = 14400) {
  n <- length(y); D <- diff(diag(n), differences = 2)
  as.numeric(solve(diag(n) + lambda * crossprod(D), y))
}
