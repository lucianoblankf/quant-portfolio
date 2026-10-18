# 04: figures.

source("R/pairs.R")
source("R/plots.R")

cli::cli_h1("04 Figures")

config <- pairs_config()
prices <- readRDS("data/processed/prices.rds")
selected <- readRDS("data/processed/selected_pairs.rds")
portfolio <- readRDS("data/processed/portfolio_returns.rds")
scan <- readr::read_csv("tabs/formation_scan.csv", show_col_types = FALSE)
dir.create("figs", showWarnings = FALSE)

top <- selected[1, ]
ggplot2::ggsave(
  "figs/spread_top_pair.png",
  plot_spread(prices$date, log(prices[[top$y]]), log(prices[[top$x]]), top$beta,
              toupper(top$y), toupper(top$x), config$formation_end),
  width = 9, height = 4.5, dpi = 300
)
ggplot2::ggsave("figs/equity_curve.png", plot_equity(portfolio), width = 9, height = 4, dpi = 300)
ggplot2::ggsave("figs/adf_scan.png", plot_adf_scan(scan, config$adf_cv_5pct), width = 7, height = 4, dpi = 300)

cli::cli_alert_success("Figures saved to {.path figs/}")
