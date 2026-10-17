# Project 2: does volatility clustering break VaR? GARCH vs historical vs EWMA.
# Run with:  Rscript analysis.R   (takes a minute or two: rolling re-estimation)

suppressPackageStartupMessages({ library(ggplot2); library(moments); library(tseries) })

args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))), error = function(e) getwd())
if (length(here) == 0 || is.na(here)) here <- getwd()
source(file.path(here, "garch_var.R"))
dir.create(file.path(here, "figures"), showWarnings = FALSE)
dir.create(file.path(here, "results"), showWarnings = FALSE)
data_file <- file.path(here, "data", "prices.csv")

if (!file.exists(data_file)) {
  suppressPackageStartupMessages(library(quantmod))
  x <- suppressWarnings(getSymbols("^BVSP", src = "yahoo", from = "2010-01-01", auto.assign = FALSE))
  dir.create(dirname(data_file), showWarnings = FALSE)
  write.csv(data.frame(date = index(x), Ibovespa = as.numeric(Cl(x))), data_file, row.names = FALSE)
}
px <- read.csv(data_file, check.names = FALSE); px$date <- as.Date(px$date)
px <- px[!is.na(px$Ibovespa), ]
r <- diff(log(px$Ibovespa)); dates <- px$date[-1]
cat(sprintf("Ibovespa: %d returns, %s to %s\n", length(r), min(dates), max(dates)))

# ---- 1. Is there volatility clustering? ----------------------------------------
lb_r  <- Box.test(r,   lag = 10, type = "Ljung-Box")
lb_r2 <- Box.test(r^2, lag = 10, type = "Ljung-Box")
cat(sprintf("\nLjung-Box (10 lags): returns p = %.4f | squared returns p = %.2e\n",
            lb_r$p.value, lb_r2$p.value))
acf_df <- data.frame(lag = 1:30, acf = c(acf(r^2, lag.max = 30, plot = FALSE)$acf[-1]))
g <- ggplot(acf_df, aes(lag, acf)) + geom_col(fill = "#4C78A8") +
  geom_hline(yintercept = c(-1, 1) * 1.96 / sqrt(length(r)), linetype = 2, colour = "#E45756") +
  labs(title = "Ibovespa: autocorrelation of squared returns", x = "Lag (days)", y = "ACF") + theme_minimal()
ggsave(file.path(here, "figures", "acf_squared_returns.png"), g, width = 7, height = 4, dpi = 150)

# ---- 2. Full-sample GARCH(1,1) fits ------------------------------------------------
fits <- list(normal = fit_garch(r, "norm"), student_t = fit_garch(r, "std"))
cat("\nFull-sample GARCH(1,1) estimates\n")
fit_tbl <- do.call(rbind, lapply(names(fits), function(nm) {
  p <- fits[[nm]]$par; k <- length(p)
  data.frame(dist = nm, omega = p[1], alpha = p[2], beta = p[3],
             persistence = p[2] + p[3], nu = ifelse(k == 4, p[4], NA),
             half_life_days = log(0.5) / log(p[2] + p[3]),
             loglik = fits[[nm]]$loglik, AIC = 2 * k - 2 * fits[[nm]]$loglik)
}))
print(fit_tbl, digits = 4, row.names = FALSE)
write.csv(fit_tbl, file.path(here, "results", "garch_fit.csv"), row.names = FALSE)

# ---- 3. Rolling out-of-sample VaR --------------------------------------------------
res_file <- file.path(here, "results", "rolling_var.csv")
if (file.exists(res_file)) {
  rv <- read.csv(res_file)
} else {
  cat("\nRolling VaR forecasts (this is the slow part)...\n")
  rv <- rolling_var(r)
  rv$date <- dates[rv$index]
  write.csv(rv, res_file, row.names = FALSE)
}
rv$date <- as.Date(rv$date)
cat(sprintf("Out-of-sample: %d days, %s to %s\n", nrow(rv), min(rv$date), max(rv$date)))

models <- c("hist", "norm", "ewma", "garch", "garcht")
labels <- c(hist = "Historical (250d)", norm = "Normal (250d)", ewma = "EWMA 0.94",
            garch = "GARCH-normal", garcht = "GARCH-t")
bt <- rbind(backtest_table(rv, models, 0.95), backtest_table(rv, models, 0.99))
bt$model <- labels[bt$model]
cat("\nBacktest (Kupiec = unconditional coverage; indep = Christoffersen; cond_cov = both)\n")
print(bt, digits = 3, row.names = FALSE)
write.csv(bt, file.path(here, "results", "backtest.csv"), row.names = FALSE)

# Basel traffic light: last 250 days at 99%
last <- tail(rv, 250)
tl <- sapply(models, function(m) sum(last$ret < -last[[paste0(m, "_99")]]))
cat("\nBasel traffic light, last 250 days, 99% VaR\n")
print(data.frame(model = labels[models], breaches = tl, zone = basel_zone(tl)), row.names = FALSE)

# Crisis check: 2020
c20 <- rv[format(rv$date, "%Y") == "2020", ]
cat("\nBreaches of 99% VaR in 2020 (", nrow(c20), "days):\n")
print(sapply(models, function(m) sum(c20$ret < -c20[[paste0(m, "_99")]])))

# ---- 4. Figure: forecasts vs returns ------------------------------------------------
sel <- rv[rv$date >= as.Date("2019-06-01") & rv$date <= as.Date("2021-06-30"), ]
long <- rbind(data.frame(date = sel$date, var = sel$hist_99,   model = labels["hist"]),
              data.frame(date = sel$date, var = sel$garcht_99, model = labels["garcht"]))
g <- ggplot() +
  geom_col(data = sel, aes(date, ret), fill = "grey70", width = 1) +
  geom_line(data = long, aes(date, -var, colour = model), linewidth = 0.8) +
  scale_colour_manual(values = c("#E45756", "#4C78A8")) +
  labs(title = "99% VaR through the COVID crash: historical vs GARCH-t",
       x = NULL, y = "Daily return / -VaR", colour = NULL) +
  theme_minimal() + theme(legend.position = "bottom")
ggsave(file.path(here, "figures", "var_covid.png"), g, width = 9, height = 4.5, dpi = 150)

g2 <- ggplot(data.frame(date = rv$date, sigma = sqrt(252) * rv$garcht_99 / abs(qt(0.01, fits$student_t$par[4]) *
        sqrt((fits$student_t$par[4] - 2) / fits$student_t$par[4]))),
        aes(date, sigma)) + geom_line(colour = "#4C78A8") +
  labs(title = "GARCH-t annualised conditional volatility (out of sample)", x = NULL, y = "Volatility") +
  scale_y_continuous(labels = scales::percent) + theme_minimal()
ggsave(file.path(here, "figures", "garch_volatility.png"), g2, width = 9, height = 4, dpi = 150)
cat("\nDone.\n")
