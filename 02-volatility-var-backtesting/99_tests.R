# 99: sanity checks with known answers (parameter recovery, test behaviour).

source("R/garch.R")
source("R/var_models.R")
source("R/backtest.R")

cli::cli_h1("Tests")

check <- function(condition, message) {
  if (!isTRUE(condition)) {
    cli::cli_abort("FAILED: {message}")
  }
  cli::cli_alert_success(message)
}

# 1. GARCH recovers known parameters from simulated data
set.seed(1)
n <- 8000
true <- c(omega = 2e-6, alpha = 0.08, beta = 0.90)
r <- numeric(n)
sigma2 <- true[["omega"]] / (1 - true[["alpha"]] - true[["beta"]])
for (t in seq_len(n)) {
  r[t] <- sqrt(sigma2) * stats::rnorm(1)
  sigma2 <- true[["omega"]] + true[["alpha"]] * r[t]^2 + true[["beta"]] * sigma2
}
fit <- fit_garch(r, "norm")
check(
  abs(fit$par[[2]] - true[["alpha"]]) < 0.03 && abs(fit$par[[3]] - true[["beta"]]) < 0.04,
  "GARCH(1,1) recovers alpha and beta"
)
check(abs(fit$par[[2]] + fit$par[[3]] - 0.98) < 0.02, "GARCH persistence close to 0.98")

# 2. Kupiec and Christoffersen behave as the theory says
check(
  abs(kupiec_pof(c(rep(1, 10), rep(0, 990)), 0.01)$lr) < 1e-9,
  "Kupiec LR = 0 when the breach rate equals p"
)
check(
  kupiec_pof(c(rep(1, 30), rep(0, 970)), 0.01)$p_value < 0.001,
  "Kupiec rejects a 3% breach rate at 1% VaR"
)
clustered <- rep(0, 1000)
clustered[c(100:104, 500:504, 800:804)] <- 1
check(christoffersen_ind(clustered)$p_value < 0.01, "Christoffersen detects clustered breaches")
spread <- rep(0, 1000)
spread[seq(50, 950, by = 100)] <- 1
check(christoffersen_ind(spread)$p_value > 0.3, "Christoffersen accepts evenly spread breaches")

# 3. VaR from sigma
check(abs(var_from_sigma(0.01, 0.99) - 0.02326) < 1e-4, "99% normal VaR = 2.326 sigma")
check(
  var_from_sigma(0.01, 0.99, "std", 5) < var_from_sigma(0.01, 0.99, "std", 50) * 1.2,
  "Student-t VaR is scaled to unit variance"
)

cli::cli_alert_success("All tests passed")
