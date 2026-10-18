# 05: figures.

source("R/var_models.R")
source("R/plots.R")

cli::cli_h1("05 Figures")

returns <- readRDS("data/processed/returns.rds")
rolling <- readRDS("data/processed/rolling_var.rds")
dir.create("figs", showWarnings = FALSE)

ggplot2::ggsave(
  "figs/acf_squared_returns.png", plot_acf_squared(returns$log_return),
  width = 7, height = 4, dpi = 300
)
ggplot2::ggsave(
  "figs/var_covid.png", plot_var_window(rolling, "2019-06-01", "2021-06-30"),
  width = 9, height = 4.5, dpi = 300
)
ggplot2::ggsave(
  "figs/garch_volatility.png", plot_garch_volatility(rolling),
  width = 9, height = 4, dpi = 300
)

cli::cli_alert_success("Figures saved to {.path figs/}")
