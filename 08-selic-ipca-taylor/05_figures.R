# 05: figures.

source("R/plots.R")

cli::cli_h1("05 Figures")

dataset <- readRDS("data/processed/dataset.rds")
dynamic_rule <- readRDS("data/processed/dynamic_rule.rds")
irf_table <- readr::read_csv("tabs/irf_selic_shock.csv", show_col_types = FALSE)
dir.create("figs", showWarnings = FALSE)

ggplot2::ggsave("figs/selic_vs_ipca.png", plot_selic_ipca(dataset), width = 9, height = 4.5, dpi = 300)
ggplot2::ggsave(
  "figs/taylor_fit.png",
  plot_taylor_fit(tidyr::drop_na(dataset, selic_l1), stats::fitted(dynamic_rule)),
  width = 9, height = 4.5, dpi = 300
)
ggplot2::ggsave("figs/irf_selic_shock.png", plot_irf(irf_table), width = 9, height = 4, dpi = 300)

cli::cli_alert_success("Figures saved to {.path figs/}")
