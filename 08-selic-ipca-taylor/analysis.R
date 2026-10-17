# Project 8: how does the Banco Central react to inflation, and how does Selic affect it?
# A Taylor rule for Brazil (OLS with HAC errors, structural break) plus a small VAR with
# Granger tests and impulse responses. Data: Banco Central do Brasil SGS API, monthly.
# Run with:  Rscript analysis.R

suppressPackageStartupMessages({ library(ggplot2); library(tseries); library(sandwich); library(lmtest)
                                 library(car); library(strucchange); library(urca) })

args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))), error = function(e) getwd())
if (length(here) == 0 || is.na(here)) here <- getwd()
source(file.path(here, "var_tools.R"))
for (d in c("figures", "results", "data")) dir.create(file.path(here, d), showWarnings = FALSE)

# ---- 1. Data ---------------------------------------------------------------------------
series <- c(selic = 4189,    # Selic, % a.a., monthly average
            ipca12 = 13522,  # IPCA, 12-month change, %
            ibc = 24364,     # IBC-Br activity index, seasonally adjusted
            fx = 3698)       # USD/BRL, end of month
get_sgs <- function(id) {
  f <- file.path(here, "data", sprintf("sgs_%d.csv", id))
  if (!file.exists(f)) {
    u <- sprintf("https://api.bcb.gov.br/dados/serie/bcdata.sgs.%d/dados?formato=json&dataInicial=01/01/2003&dataFinal=31/12/2026", id)
    write.csv(jsonlite::fromJSON(u), f, row.names = FALSE)
  }
  d <- read.csv(f); d$date <- as.Date(d$data, "%d/%m/%Y"); d[, c("date", "valor")]
}
df <- Reduce(function(a, b) merge(a, b, by = "date"),
             Map(function(id, nm) setNames(get_sgs(id), c("date", nm)), series, names(series)))
df <- df[complete.cases(df), ]
df$lib <- log(df$ibc)
df$gap <- 100 * (df$lib - hp_trend(df$lib))        # output gap, % of trend (two-sided HP)
df$selic_l1 <- c(NA, head(df$selic, -1))
cat(sprintf("Monthly sample: %d obs, %s to %s\n", nrow(df), min(df$date), max(df$date)))
write.csv(df, file.path(here, "results", "dataset.csv"), row.names = FALSE)

# ---- 2. Stationarity ---------------------------------------------------------------------
ur <- function(x) c(adf_p = suppressWarnings(adf.test(x)$p.value), kpss_p = suppressWarnings(kpss.test(x)$p.value))
ur_tbl <- rbind(selic = ur(df$selic), ipca12 = ur(df$ipca12), gap = ur(df$gap),
                d_selic = ur(diff(df$selic)), d_ipca12 = ur(diff(df$ipca12)))
cat("\nUnit-root tests (ADF: H0 unit root; KPSS: H0 stationary)\n"); print(round(ur_tbl, 3))

# ---- 3. Taylor rule ------------------------------------------------------------------------
# i_t = a + b * inflation_t + c * gap_t + rho * i_{t-1} + e_t
d3 <- df[complete.cases(df), ]
hac <- function(m) NeweyWest(m, lag = 6, prewhite = FALSE)
static  <- lm(selic ~ ipca12 + gap, data = d3)
dynamic <- lm(selic ~ ipca12 + gap + selic_l1, data = d3)
cat("\nStatic Taylor rule (HAC standard errors)\n");  print(coeftest(static,  vcov. = hac(static)))
cat("\nDynamic Taylor rule with interest-rate smoothing (HAC)\n"); print(coeftest(dynamic, vcov. = hac(dynamic)))
b <- coef(dynamic); rho <- b[["selic_l1"]]
lr <- c(inflation = b[["ipca12"]] / (1 - rho), gap = b[["gap"]] / (1 - rho))
cat(sprintf("\nSmoothing rho = %.3f; long-run response: inflation %.2f, gap %.2f; R2 = %.3f\n",
            rho, lr[["inflation"]], lr[["gap"]], summary(dynamic)$r.squared))
tp <- linearHypothesis(dynamic, "ipca12 + selic_l1 = 1", vcov. = hac(dynamic))
cat(sprintf("Taylor principle (long-run inflation coefficient = 1): Wald p-value = %.3f\n", tp[2, ncol(tp)]))
cat(sprintf("Durbin-Watson-type check: residual AR(1) = %.3f\n", acf(resid(dynamic), plot = FALSE)$acf[2]))

# Subsamples and structural break
sub_fit <- function(i) { m <- lm(selic ~ ipca12 + gap + selic_l1, data = d3[i, ]); cf <- coef(m)
  c(n = sum(i), infl_SR = cf[["ipca12"]], gap_SR = cf[["gap"]], rho = cf[["selic_l1"]],
    infl_LR = cf[["ipca12"]] / (1 - cf[["selic_l1"]]), R2 = summary(m)$r.squared) }
sub_tbl <- rbind(`2003-2015` = sub_fit(d3$date < as.Date("2016-01-01")),
                 `2016-2026` = sub_fit(d3$date >= as.Date("2016-01-01")))
cat("\nTaylor rule by sub-period\n"); print(round(sub_tbl, 3))
bp <- breakpoints(selic ~ ipca12 + gap + selic_l1, data = d3, h = 0.15)
cat("\nBai-Perron breakpoints (BIC-selected):", paste(d3$date[bp$breakpoints], collapse = ", "), "\n")
chow <- sctest(selic ~ ipca12 + gap + selic_l1, data = d3, type = "supF", from = 0.15)
cat(sprintf("supF test of parameter stability: F = %.1f, p = %.4f\n", chow$statistic, chow$p.value))
write.csv(sub_tbl, file.path(here, "results", "taylor_subsamples.csv"))

# ---- 4. Cointegration of Selic and inflation -----------------------------------------------
jo <- ca.jo(df[, c("selic", "ipca12")], type = "trace", ecdet = "const", K = 3)
cat("\nJohansen trace test (selic, ipca12)\n")
print(data.frame(H0 = c("r <= 1", "r = 0"), trace = jo@teststat, crit_5pct = jo@cval[, "5pct"]), row.names = FALSE)

# ---- 5. VAR and impulse responses -----------------------------------------------------------
Y <- as.matrix(df[, c("gap", "ipca12", "selic")])    # ordering: policy rate last (recursive identification)
sel <- var_select(Y, 8); cat("\nVAR lag selection\n"); print(round(sel, 3), row.names = FALSE)
p <- sel$p[which.min(sel$BIC)]
fit <- var_fit(Y, p)
cat(sprintf("\nVAR(%d) on levels of (gap, ipca12, selic); %d observations\n", p, fit$T))
gr <- rbind(`selic -> ipca12` = granger(fit, "selic", "ipca12"), `ipca12 -> selic` = granger(fit, "ipca12", "selic"),
            `gap -> selic` = granger(fit, "gap", "selic"),       `selic -> gap` = granger(fit, "selic", "gap"),
            `gap -> ipca12` = granger(fit, "gap", "ipca12"),     `ipca12 -> gap` = granger(fit, "ipca12", "gap"))
cat("\nGranger causality (F tests)\n"); print(round(gr, 4))
write.csv(gr, file.path(here, "results", "granger.csv"))

H <- 36
irf <- var_irf_boot(fit, "selic", H = H, R = 300)
ci <- match("ipca12", colnames(Y)); gi <- match("gap", colnames(Y))
cat(sprintf("\nResponse of IPCA 12m to a 1 s.d. Selic shock (%.2f p.p.): peak %.3f p.p. at month %d; 90%% band at peak [%.3f, %.3f]\n",
            sqrt(fit$Sigma[3, 3]), irf$point[which.max(abs(irf$point[, ci])), ci], which.max(abs(irf$point[, ci])) - 1,
            irf$lo[which.max(abs(irf$point[, ci])), ci], irf$hi[which.max(abs(irf$point[, ci])), ci]))
cat(sprintf("Response of the output gap: peak %.3f at month %d\n",
            irf$point[which.max(abs(irf$point[, gi])), gi], which.max(abs(irf$point[, gi])) - 1))

irf_df <- do.call(rbind, lapply(c("ipca12", "gap"), function(v) {
  j <- match(v, colnames(Y))
  data.frame(h = 0:H, resp = irf$point[, j], lo = irf$lo[, j], hi = irf$hi[, j],
             variable = ifelse(v == "ipca12", "IPCA 12m (p.p.)", "Output gap (% of trend)"))
}))
write.csv(irf_df, file.path(here, "results", "irf_selic_shock.csv"), row.names = FALSE)

# Robustness: add the exchange rate to the VAR (a forward-looking price helps with the price puzzle).
Y4 <- cbind(gap = df$gap, lfx = 100 * log(df$fx), ipca12 = df$ipca12, selic = df$selic)
sel4 <- var_select(Y4, 8); p4 <- sel4$p[which.min(sel4$BIC)]
fit4 <- var_fit(Y4, p4)
irf4 <- var_irf_boot(fit4, "selic", H = H, R = 300)
ci4 <- match("ipca12", colnames(Y4)); k4 <- which.max(abs(irf4$point[, ci4]))
cat(sprintf("
VAR(%d) with FX: IPCA 12m response to a Selic shock: peak %.3f at month %d, band [%.3f, %.3f]; at month 24: %.3f [%.3f, %.3f]
",
            p4, irf4$point[k4, ci4], k4 - 1, irf4$lo[k4, ci4], irf4$hi[k4, ci4],
            irf4$point[25, ci4], irf4$lo[25, ci4], irf4$hi[25, ci4]))
cat(sprintf("Baseline VAR at month 24: %.3f [%.3f, %.3f]
", irf$point[25, ci], irf$lo[25, ci], irf$hi[25, ci]))
irf4_df <- data.frame(h = 0:H, resp = irf4$point[, ci4], lo = irf4$lo[, ci4], hi = irf4$hi[, ci4])
write.csv(irf4_df, file.path(here, "results", "irf_ipca_with_fx.csv"), row.names = FALSE)

# ---- 6. Figures --------------------------------------------------------------------------------
ggsave(file.path(here, "figures", "selic_vs_ipca.png"),
  ggplot(reshape2_long <- data.frame(date = rep(df$date, 2), value = c(df$selic, df$ipca12),
                                    series = rep(c("Selic (% a.a.)", "IPCA 12m (%)"), each = nrow(df))),
         aes(date, value, colour = series)) + geom_line(linewidth = 0.7) +
    scale_colour_manual(values = c("#E45756", "#4C78A8")) +
    labs(title = "Selic and 12-month inflation", x = NULL, y = "%", colour = NULL) + theme_minimal() +
    theme(legend.position = "bottom"), width = 9, height = 4.5, dpi = 150)

d3$fitted <- fitted(dynamic)
ggsave(file.path(here, "figures", "taylor_fit.png"),
  ggplot(d3, aes(date)) + geom_line(aes(y = selic, colour = "Actual Selic")) +
    geom_line(aes(y = fitted, colour = "Taylor rule (dynamic)"), linetype = 2) +
    scale_colour_manual(values = c("black", "#E45756")) +
    labs(title = "Selic: actual vs dynamic Taylor rule", x = NULL, y = "% a.a.", colour = NULL) +
    theme_minimal() + theme(legend.position = "bottom"), width = 9, height = 4.5, dpi = 150)

ggsave(file.path(here, "figures", "irf_selic_shock.png"),
  ggplot(irf_df, aes(h, resp)) + geom_ribbon(aes(ymin = lo, ymax = hi), fill = "#4C78A8", alpha = 0.25) +
    geom_line(colour = "#4C78A8", linewidth = 1) + geom_hline(yintercept = 0, linetype = 2) +
    facet_wrap(~variable, scales = "free_y") +
    labs(title = "Response to a one-s.d. Selic shock (90% bootstrap bands)", x = "Months after the shock", y = NULL) +
    theme_minimal(), width = 9, height = 4, dpi = 150)
cat("\nDone.\n")
