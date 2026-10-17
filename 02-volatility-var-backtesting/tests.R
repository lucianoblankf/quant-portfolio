# Sanity checks with known answers. Run with:  Rscript tests.R
args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))), error = function(e) getwd())
source(file.path(here, "garch_var.R"))
ok <- function(cond, msg) { if (!isTRUE(cond)) stop("FAILED: ", msg); cat("ok  ", msg, "\n") }

# 1. GARCH recovers known parameters from simulated data
set.seed(1)
n <- 8000; omega <- 2e-6; a <- 0.08; b <- 0.90
r <- numeric(n); s2 <- omega / (1 - a - b)
for (t in 1:n) { r[t] <- sqrt(s2) * rnorm(1); s2 <- omega + a * r[t]^2 + b * s2 }
f <- fit_garch(r, "norm")
ok(abs(f$par[2] - a) < 0.03 && abs(f$par[3] - b) < 0.04, "GARCH(1,1) recovers alpha and beta")
ok(abs(f$par[2] + f$par[3] - 0.98) < 0.02, "GARCH persistence close to 0.98")

# 2. Kupiec: exactly the expected number of breaches gives LR = 0
h <- c(rep(1, 10), rep(0, 990))
ok(abs(kupiec_pof(h, 0.01)[["LR"]]) < 1e-9, "Kupiec LR = 0 when breach rate equals p")
# 3. Kupiec rejects 3x too many breaches
h <- c(rep(1, 30), rep(0, 970))
ok(kupiec_pof(h, 0.01)[["p_value"]] < 0.001, "Kupiec rejects 3% breach rate at 1% VaR")
# 4. Christoffersen detects clustering
h <- rep(0, 1000); h[c(100:104, 500:504, 800:804)] <- 1
ok(christoffersen_ind(h)[["p_value"]] < 0.01, "Christoffersen detects clustered breaches")
h <- rep(0, 1000); h[seq(50, 950, by = 100)] <- 1
ok(christoffersen_ind(h)[["p_value"]] > 0.3, "Christoffersen accepts evenly spread breaches")
# 5. Normal VaR textbook value
ok(abs(var_from_sigma(0.01, 0.99) - 0.02326) < 1e-4, "99% normal VaR = 2.326 sigma")
# 6. Student-t VaR is standardised to unit variance
ok(var_from_sigma(0.01, 0.99, "std", 5) < var_from_sigma(0.01, 0.99, "std", 50) * 1.2, "t VaR is variance-scaled")
cat("All tests passed.\n")
