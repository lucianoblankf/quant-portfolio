# Project 1 (R mirror): are Brazilian market returns normal, and what does that do to VaR?
# Run with:  Rscript analysis.R
# Reproduces the Python tables (risk.py / analysis.py) so the two can be cross-checked.
# Prices are cached in data/prices.csv (same layout as the Python cache).

suppressPackageStartupMessages({
  library(quantmod)
  library(moments)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))),
                 error = function(e) getwd())
if (length(here) == 0 || is.na(here)) here <- getwd()
data_file <- file.path(here, "data", "prices.csv")
fig_dir   <- file.path(here, "figures")
res_dir   <- file.path(here, "results")
dir.create(fig_dir, showWarnings = FALSE); dir.create(res_dir, showWarnings = FALSE)

tickers <- c("^BVSP" = "Ibovespa", "BRL=X" = "USD/BRL")
alphas  <- c(0.95, 0.99)

# ---- risk functions (same conventions as risk.py: VaR / ES are positive losses) ----
log_returns    <- function(p) diff(log(p))
jarque_bera    <- function(r) {
  n <- length(r); s <- skewness(r); k <- kurtosis(r) - 3
  jb <- n / 6 * (s^2 + k^2 / 4)
  c(statistic = jb, p_value = pchisq(jb, df = 2, lower.tail = FALSE))
}
historical_var <- function(r, alpha) -unname(quantile(r, 1 - alpha, type = 7))
parametric_var <- function(r, alpha) -(mean(r) + sd(r) * qnorm(1 - alpha))
historical_es  <- function(r, alpha) { q <- quantile(r, 1 - alpha, type = 7); -mean(r[r <= q]) }

# ---- data ----
load_prices <- function() {
  if (file.exists(data_file)) {
    d <- read.csv(data_file, check.names = FALSE); d$date <- as.Date(d$date); return(d)
  }
  out <- NULL
  for (tk in names(tickers)) {
    x <- suppressWarnings(getSymbols(tk, src = "yahoo", from = "2010-01-01", auto.assign = FALSE))
    x <- data.frame(date = index(x), Cl(x)); names(x)[2] <- tickers[[tk]]
    out <- if (is.null(out)) x else merge(out, x, by = "date", all = TRUE)
  }
  dir.create(dirname(data_file), showWarnings = FALSE)
  write.csv(out, data_file, row.names = FALSE)
  out
}

prices <- load_prices()
rets <- lapply(tickers, function(nm) {
  p <- prices[!is.na(prices[[nm]]), c("date", nm)]
  data.frame(date = p$date[-1], r = log_returns(p[[nm]]))
})
names(rets) <- tickers

stats_tbl <- sapply(rets, function(d) {
  r <- d$r; jb <- jarque_bera(r)
  c(n = length(r), mean = mean(r), vol = sd(r), ann_vol = sd(r) * sqrt(252),
    skew = skewness(r), excess_kurtosis = kurtosis(r) - 3,
    jarque_bera = jb[["statistic"]], jb_p_value = jb[["p_value"]])
})

var_tbl <- do.call(rbind, lapply(names(rets), function(nm) {
  r <- rets[[nm]]$r
  do.call(rbind, lapply(alphas, function(a) {
    h <- historical_var(r, a); p <- parametric_var(r, a)
    data.frame(asset = nm, confidence = sprintf("%.0f%%", 100 * a),
               historical_var = h, parametric_var = p, hist_over_param = h / p,
               historical_es = historical_es(r, a),
               param_breach_rate = mean(r < -p), expected_breach_rate = 1 - a)
  }))
}))

cat("\nDescriptive statistics\n"); print(round(stats_tbl, 4))
cat("\n1-day VaR and ES\n"); print(var_tbl, digits = 4, row.names = FALSE)
cat("\nFive worst days\n")
for (nm in names(rets)) {
  d <- rets[[nm]]; w <- d[order(d$r)[1:5], ]
  cat(nm, "->", paste0(w$date, " (", sprintf("%+.1f%%", 100 * w$r), ")", collapse = ", "), "\n")
}
write.csv(t(stats_tbl), file.path(res_dir, "stats_R.csv"))
write.csv(var_tbl, file.path(res_dir, "var_R.csv"), row.names = FALSE)

# ---- figures ----
for (nm in names(rets)) {
  r <- rets[[nm]]$r
  slug <- gsub("[/ ]", "", tolower(nm))
  g <- ggplot(data.frame(r = r), aes(r)) +
    geom_histogram(aes(y = after_stat(density)), bins = 120, fill = "#4C78A8", alpha = 0.75) +
    stat_function(fun = dnorm, args = list(mean(r), sd(r)), colour = "#E45756", linewidth = 1) +
    scale_y_log10(limits = c(1e-2, NA)) +
    labs(title = paste(nm, ": daily log returns vs the normal"), x = "Daily log return",
         y = "Density (log scale)") + theme_minimal()
  ggsave(file.path(fig_dir, paste0("hist_", slug, "_R.png")), g, width = 8, height = 4.5, dpi = 150)
  z <- data.frame(s = sort((r - mean(r)) / sd(r)))
  z$q <- qnorm(ppoints(nrow(z)))
  g2 <- ggplot(z, aes(q, s)) + geom_point(size = 0.6, colour = "#4C78A8") +
    geom_abline(colour = "#E45756") + coord_equal() +
    labs(title = paste(nm, ": QQ plot against the normal"), x = "Normal quantiles",
         y = "Observed quantiles (standardised)") + theme_minimal()
  ggsave(file.path(fig_dir, paste0("qq_", slug, "_R.png")), g2, width = 5.5, height = 5.5, dpi = 150)
}
cat("\nFigures saved to", fig_dir, "\n")
