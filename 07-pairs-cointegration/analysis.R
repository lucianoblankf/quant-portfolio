# Project 7: cointegration and pairs trading on Brazilian stocks.
# Run with:  Rscript analysis.R
#
# Design (everything out of sample):
#   formation window  2015-01 to 2019-12: test every pair for cointegration (Engle-Granger),
#                     estimate the hedge ratio and pick the pairs that pass
#   trading window    2020-01 to today:   trade the selected pairs with a fixed hedge ratio
#                     and check whether cointegration survived

suppressPackageStartupMessages({ library(quantmod); library(tseries); library(ggplot2); library(dplyr) })

args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))), error = function(e) getwd())
if (length(here) == 0 || is.na(here)) here <- getwd()
source(file.path(here, "pairs.R"))
for (d in c("figures", "results", "data")) dir.create(file.path(here, d), showWarnings = FALSE)

tickers <- c("PETR3", "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "GGBR4", "GOAU4", "ELET3", "ELET6",
             "CMIG4", "CPLE6", "ABEV3", "WEGE3", "SUZB3", "CSNA3", "USIM5", "BRFS3")
data_file <- file.path(here, "data", "prices.csv")
if (!file.exists(data_file)) {
  cat("Downloading prices...\n")
  lst <- lapply(tickers, function(tk) {
    x <- tryCatch(suppressWarnings(getSymbols(paste0(tk, ".SA"), src = "yahoo", from = "2015-01-01", auto.assign = FALSE)),
                  error = function(e) NULL)
    if (is.null(x)) return(NULL)
    setNames(data.frame(date = index(x), as.numeric(Ad(x))), c("date", tk))
  })
  lst <- Filter(Negate(is.null), lst)
  px <- Reduce(function(a, b) merge(a, b, by = "date", all = TRUE), lst)
  write.csv(px, data_file, row.names = FALSE)
}
px <- read.csv(data_file); px$date <- as.Date(px$date)
px <- px[complete.cases(px), ]
cat(sprintf("%d stocks, %d days (%s to %s)\n", ncol(px) - 1, nrow(px), min(px$date), max(px$date)))

form  <- px[px$date <  as.Date("2020-01-01"), ]
trade <- px[px$date >= as.Date("2020-01-01"), ]
lp <- function(d) log(as.matrix(d[, -1]))

# ---- 1. Scan all pairs in the formation window -----------------------------------------
nm <- names(px)[-1]
pairs <- t(combn(nm, 2))
scan <- do.call(rbind, lapply(seq_len(nrow(pairs)), function(i) {
  y <- lp(form)[, pairs[i, 1]]; x <- lp(form)[, pairs[i, 2]]
  eg <- engle_granger(y, x)
  data.frame(y = pairs[i, 1], x = pairs[i, 2], beta = eg$beta, adf = eg$adf, half_life = eg$half_life)
}))
scan <- scan[order(scan$adf), ]
cv5 <- -3.34; cv1 <- -3.90          # MacKinnon (1991) critical values, 2 variables, with constant
cat(sprintf("\nFormation window: %d pairs tested; %d cointegrated at 5%% (expected by chance: about %d)\n",
            nrow(scan), sum(scan$adf < cv5), round(0.05 * nrow(scan))))
cat("\nTop 8 pairs by Engle-Granger ADF statistic (more negative = stronger)\n")
print(head(scan, 8), digits = 3, row.names = FALSE)
write.csv(scan, file.path(here, "results", "formation_scan.csv"), row.names = FALSE)

# ---- 2. Does cointegration survive out of sample? --------------------------------------
sel <- scan[scan$adf < cv5 & scan$half_life > 2 & scan$half_life < 60, ]
sel <- head(sel, 6)
cat(sprintf("\nSelected %d pairs (ADF < %.2f and half-life between 2 and 60 days)\n", nrow(sel), cv5))
oos <- do.call(rbind, lapply(seq_len(nrow(sel)), function(i) {
  y <- lp(trade)[, sel$y[i]]; x <- lp(trade)[, sel$x[i]]
  spread_fixed <- y - sel$beta[i] * x                       # formation hedge ratio
  eg_new <- engle_granger(y, x)                             # re-estimated on the trading window
  data.frame(pair = paste(sel$y[i], sel$x[i], sep = "/"), form_adf = sel$adf[i], form_hl = sel$half_life[i],
             oos_adf_fixed_beta = adf.test(spread_fixed, k = 1)$statistic[[1]],
             oos_adf_refit = eg_new$adf, oos_beta = eg_new$beta, form_beta = sel$beta[i])
}))
cat("\nOut-of-sample stability of the selected pairs\n"); print(oos, digits = 3, row.names = FALSE)
write.csv(oos, file.path(here, "results", "oos_stability.csv"), row.names = FALSE)

# ---- 3. Trade the spread ----------------------------------------------------------------
cost_bp <- 10     # per side, on traded notional
res <- lapply(seq_len(nrow(sel)), function(i) {
  y <- lp(trade)[, sel$y[i]]; x <- lp(trade)[, sel$x[i]]
  bt <- backtest_pair(y, x, sel$beta[i], dates = trade$date, entry = 2, exit = 0.5, stop = 4,
                      lookback = 60, cost = cost_bp / 1e4)
  bt$pair <- paste(sel$y[i], sel$x[i], sep = "/"); bt
})
names(res) <- paste(sel$y, sel$x, sep = "/")
perf <- as.data.frame(do.call(rbind, lapply(res, function(b) perf_stats(b$ret, b$trades, b$wins))))
perf$pair <- rownames(perf); rownames(perf) <- NULL
perf <- perf[, c("pair", setdiff(names(perf), "pair"))]
cat(sprintf("\nTrading window performance (entry |z|>2, exit |z|<0.5, stop |z|>4, %d bp per side)\n", cost_bp))
print(perf, digits = 3, row.names = FALSE)
write.csv(perf, file.path(here, "results", "performance.csv"), row.names = FALSE)

# Equal-weight portfolio of the selected pairs
port <- Reduce(`+`, lapply(res, function(b) b$ret)) / length(res)
pp <- perf_stats(port, sum(perf$trades), sum(perf$wins))
cat("\nEqual-weight portfolio of selected pairs\n"); print(round(pp, 3))
sub <- function(from, to) { i <- trade$date >= as.Date(from) & trade$date <= as.Date(to); round(perf_stats(port[i], NA, NA)[c("ann_return", "ann_vol", "sharpe")], 3) }
cat("\nPortfolio by sub-period\n")
print(rbind(`2020-2021` = sub("2020-01-01", "2021-12-31"), `2022-2023` = sub("2022-01-01", "2023-12-31"),
            `2024-` = sub("2024-01-01", "2099-01-01")))

# ---- 4. Figures ---------------------------------------------------------------------------
top <- sel[1, ]
yb <- log(px[[top$y]]); xb <- log(px[[top$x]])
dfp <- data.frame(date = px$date, spread = yb - top$beta * xb,
                  window = ifelse(px$date < as.Date("2020-01-01"), "Formation", "Trading"))
g <- ggplot(dfp, aes(date, spread, colour = window)) + geom_line(linewidth = 0.4) +
  geom_vline(xintercept = as.Date("2020-01-01"), linetype = 2) +
  scale_colour_manual(values = c("#4C78A8", "#E45756")) +
  labs(title = sprintf("Spread %s / %s with the formation hedge ratio (%.2f)", top$y, top$x, top$beta),
       subtitle = "Stationary in formation, then it drifts: cointegration did not hold out of sample",
       x = NULL, y = "log(Y) - beta * log(X)", colour = NULL) + theme_minimal()
ggsave(file.path(here, "figures", "spread_top_pair.png"), g, width = 9, height = 4.5, dpi = 150)

eq <- data.frame(date = trade$date, equity = cumprod(1 + port))
g2 <- ggplot(eq, aes(date, equity)) + geom_line(colour = "#4C78A8") +
  geom_hline(yintercept = 1, linetype = 2, colour = "grey50") +
  labs(title = "Equal-weight portfolio of selected pairs, out of sample (after costs)", x = NULL, y = "Growth of 1") +
  theme_minimal()
ggsave(file.path(here, "figures", "equity_curve.png"), g2, width = 9, height = 4, dpi = 150)

g3 <- ggplot(scan, aes(adf)) + geom_histogram(bins = 30, fill = "#4C78A8") +
  geom_vline(xintercept = cv5, colour = "#E45756", linetype = 2) +
  labs(title = "Engle-Granger statistics for all pairs (formation window)",
       subtitle = "Red line: 5% critical value", x = "ADF statistic of the residual", y = "Pairs") + theme_minimal()
ggsave(file.path(here, "figures", "adf_scan.png"), g3, width = 7, height = 4, dpi = 150)
cat("\nDone.\n")
