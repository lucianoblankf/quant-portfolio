# 04: figures.

source("R/pca.R")
source("R/plots.R")

cli::cli_h1("04 Figures")

curve <- readRDS("data/processed/curve.rds")
fit <- readRDS("data/processed/pca_fit.rds")
dir.create("figs", showWarnings = FALSE)

ggplot2::ggsave("figs/curve_history.png", plot_curve_history(curve), width = 9, height = 4.5, dpi = 300)
ggplot2::ggsave("figs/loadings.png", plot_loadings(loadings_table(fit)), width = 7, height = 4.5, dpi = 300)
ggplot2::ggsave("figs/scree.png", plot_scree(variance_table(fit)), width = 6, height = 4, dpi = 300)

cli::cli_alert_success("Figures saved to {.path figs/}")
