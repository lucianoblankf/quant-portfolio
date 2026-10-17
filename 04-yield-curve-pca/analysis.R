# Project 4: PCA of the Brazilian pre-fixed yield curve (level, slope, curvature).
# Run with:  Rscript analysis.R
# Data: Tesouro Direto "Tesouro Prefixado" (LTN, zero-coupon) yields published by
# Tesouro Transparente, cached in data/tesouro_direto.csv (downloaded on first run).

suppressPackageStartupMessages({ library(ggplot2); library(tidyr); library(dplyr) })

args <- commandArgs(trailingOnly = FALSE)
here <- tryCatch(dirname(normalizePath(sub("--file=", "", args[grep("--file=", args)]))), error = function(e) getwd())
if (length(here) == 0 || is.na(here)) here <- getwd()
dir.create(file.path(here, "figures"), showWarnings = FALSE)
dir.create(file.path(here, "results"), showWarnings = FALSE)
src <- file.path(here, "data", "tesouro_direto.csv")
if (!file.exists(src)) {
  dir.create(dirname(src), showWarnings = FALSE)
  download.file("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv",
                src, mode = "wb")
}

# ---- 1. Constant-maturity zero curve ------------------------------------------------
raw <- read.csv2(src, stringsAsFactors = FALSE, check.names = FALSE)   # sep ';', decimal ','
raw <- raw[raw$`Tipo Titulo` == "Tesouro Prefixado", ]
raw$base <- as.Date(raw$`Data Base`, "%d/%m/%Y")
raw$mat  <- as.Date(raw$`Data Vencimento`, "%d/%m/%Y")
raw$ttm  <- as.numeric(raw$mat - raw$base) / 365.25
raw$y    <- raw$`Taxa Compra Manha` / 100

tenors <- c(1, 2, 3, 5)
curve <- do.call(rbind, lapply(split(raw, raw$base), function(d) {
  d <- d[order(d$ttm), ]
  if (nrow(d) < 3 || min(d$ttm) > min(tenors) || max(d$ttm) < max(tenors)) return(NULL)
  # Linear interpolation in yield between the two bonds around each tenor.
  data.frame(date = d$base[1], t(approx(d$ttm, d$y, xout = tenors)$y))
}))
names(curve) <- c("date", paste0("y", tenors, "y"))
rownames(curve) <- NULL
cat(sprintf("Curve built on %d of %d trading days (%s to %s); tenors: %s years\n",
            nrow(curve), length(unique(raw$base)), min(curve$date), max(curve$date),
            paste(tenors, collapse = ", ")))
write.csv(curve, file.path(here, "results", "constant_maturity_curve.csv"), row.names = FALSE)

# ---- 2. PCA on weekly changes (bp) ------------------------------------------------------
# Daily changes are noisy because the Tesouro Direto quote is a morning snapshot.
# Weekly (non-overlapping, last observation of each week) changes are cleaner.
curve$week <- format(curve$date, "%G-%V")
wk <- curve %>% group_by(week) %>% slice_tail(n = 1) %>% ungroup()
ycols <- grep("^y", names(wk), value = TRUE)

# Weekly changes, dropping any change that spans a gap of more than 10 days.
gap <- c(NA, diff(as.numeric(wk$date)))
chg <- as.data.frame(lapply(wk[ycols], function(x) c(NA, diff(x) * 1e4)))   # basis points
chg$date <- wk$date
chg$lv <- c(NA, diff((wk$y1y + wk$y2y + wk$y3y + wk$y5y) / 4)) * 1e4
chg$sl <- c(NA, diff(wk$y5y - wk$y1y)) * 1e4
chg$cv <- c(NA, diff(2 * wk$y2y - wk$y1y - wk$y3y)) * 1e4
chg <- chg[!is.na(gap) & gap <= 10, ]
cat(sprintf("%d weekly changes\n", nrow(chg)))

pca <- prcomp(chg[ycols], center = TRUE, scale. = FALSE)     # covariance PCA: bp are comparable units
var_expl <- pca$sdev^2 / sum(pca$sdev^2)
load <- pca$rotation
# Sign conventions: PC1 up = all rates up; PC2 up = long end up vs short end; PC3 up = belly above wings.
if (sum(load[, 1]) < 0) { load[, 1] <- -load[, 1]; pca$x[, 1] <- -pca$x[, 1] }
if (load[length(ycols), 2] < load[1, 2]) { load[, 2] <- -load[, 2]; pca$x[, 2] <- -pca$x[, 2] }
if (mean(load[2:3, 3]) < mean(load[c(1, 4), 3])) { load[, 3] <- -load[, 3]; pca$x[, 3] <- -pca$x[, 3] }

cat("\nVariance explained\n")
print(round(rbind(share = var_expl, cumulative = cumsum(var_expl)), 4))
cat("\nLoadings\n"); print(round(load, 3))
cat("\nPC standard deviations (bp per week)\n"); print(round(pca$sdev, 2))

# Do the PCs mean what we call them? Compare with simple level / slope / curvature measures.
cors <- c(level = cor(pca$x[, 1], chg$lv), slope = cor(pca$x[, 2], chg$sl), curvature = cor(pca$x[, 3], chg$cv))
cat("\nCorrelation of PC scores with simple factors (PC1~level, PC2~slope, PC3~curvature)\n")
print(round(cors, 3))

# ---- 3. Stability across sub-periods -------------------------------------------------------
split_date <- as.Date("2019-01-01")
sub_tbl <- do.call(rbind, lapply(list(early = chg$date < split_date, late = chg$date >= split_date), function(i) {
  p <- prcomp(chg[i, ycols], center = TRUE, scale. = FALSE)
  s <- p$rotation; if (sum(s[, 1]) < 0) s[, 1] <- -s[, 1]
  ve <- p$sdev^2 / sum(p$sdev^2)
  data.frame(n = sum(i), weekly_vol_bp_PC1 = p$sdev[1], PC1 = ve[1], PC2 = ve[2], PC3 = ve[3])
}))
cat("\nBy sub-period (before / from 2019)\n"); print(round(sub_tbl, 3))

# ---- 4. Stress scenarios in PC space --------------------------------------------------------
# Shift the latest curve by +/- 3 standard deviations of each factor and revalue a
# zero-coupon bond at each tenor: return = (1+y_old)^t / (1+y_new)^t - 1 (t held fixed).
last <- tail(curve, 1)[ycols] |> unlist()
scen <- do.call(rbind, lapply(1:3, function(j) {
  do.call(rbind, lapply(c(-3, 3), function(k) {
    shift_bp <- k * pca$sdev[j] * load[, j]
    y_new <- last + shift_bp / 1e4
    pnl <- (1 + last)^tenors / (1 + y_new)^tenors - 1
    data.frame(factor = paste0("PC", j), shock_sd = k, t(round(c(shift_bp, 100 * pnl), 2)))
  }))
}))
names(scen)[3:10] <- c(paste0("d", tenors, "y_bp"), paste0("ret", tenors, "y_pct"))
cat("\nStress scenarios: +/-3 sd of each factor, applied to the latest curve\n"); print(scen, row.names = FALSE)
write.csv(scen, file.path(here, "results", "pc_stress.csv"), row.names = FALSE)

# ---- 5. Reconstruction error -----------------------------------------------------------------
X <- as.matrix(sweep(chg[ycols], 2, pca$center))
recon_err <- sapply(1:4, function(k) {
  fit <- pca$x[, 1:k, drop = FALSE] %*% t(pca$rotation[, 1:k, drop = FALSE])
  sqrt(mean((X - fit)^2))
})
cat("\nRMSE of weekly changes rebuilt from k factors (bp)\n"); print(round(setNames(recon_err, paste0("k=", 1:4)), 2))

# ---- 6. Figures ------------------------------------------------------------------------------
long <- curve |> select(date, all_of(ycols)) |> pivot_longer(-date, names_to = "tenor", values_to = "y")
long$tenor <- factor(long$tenor, levels = ycols, labels = paste0(tenors, "y"))
ggsave(file.path(here, "figures", "curve_history.png"),
  ggplot(long, aes(date, y, colour = tenor)) + geom_line(linewidth = 0.5) +
    scale_y_continuous(labels = scales::percent) +
    labs(title = "Constant-maturity pre-fixed zero curve", x = NULL, y = "Yield (a.a.)", colour = "Tenor") +
    theme_minimal(), width = 9, height = 4.5, dpi = 150)

ld <- as.data.frame(load[, 1:3]); ld$tenor <- paste0(tenors, "y")
ld <- pivot_longer(ld, -tenor, names_to = "factor", values_to = "loading")
ld$tenor <- factor(ld$tenor, levels = paste0(tenors, "y"))
ggsave(file.path(here, "figures", "loadings.png"),
  ggplot(ld, aes(tenor, loading, colour = factor, group = factor)) + geom_line(linewidth = 1) + geom_point(size = 2) +
    geom_hline(yintercept = 0, linetype = 2, colour = "grey50") +
    scale_colour_manual(values = c("#4C78A8", "#F58518", "#54A24B"),
                        labels = c("PC1 (level)", "PC2 (slope)", "PC3 (curvature)")) +
    labs(title = "Principal-component loadings", x = "Tenor", y = "Loading", colour = NULL) + theme_minimal(),
  width = 7, height = 4.5, dpi = 150)

ve <- data.frame(pc = factor(paste0("PC", 1:4)), share = var_expl)
ggsave(file.path(here, "figures", "scree.png"),
  ggplot(ve, aes(pc, share)) + geom_col(fill = "#4C78A8") +
    geom_text(aes(label = scales::percent(share, 0.1)), vjust = -0.4) +
    scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
    labs(title = "Share of weekly yield-change variance by factor", x = NULL, y = NULL) + theme_minimal(),
  width = 6, height = 4, dpi = 150)
cat("\nDone.\n")
