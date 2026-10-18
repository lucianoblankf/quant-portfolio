# 03: histogram and QQ plot for each asset.

source("R/data.R")
source("R/plots.R")

cli::cli_h1("03 Figures")

returns <- readRDS("data/processed/returns.rds")
labels <- asset_labels()
dir.create("figs", showWarnings = FALSE)

returns |>
  dplyr::group_by(asset) |>
  dplyr::group_split() |>
  purrr::walk(\(d) {
    asset <- d$asset[1]
    label <- labels$label[labels$asset == asset]

    ggplot2::ggsave(
      file.path("figs", paste0("hist_", asset, ".png")),
      plot_histogram(d$log_return, label),
      width = 8, height = 4.5, dpi = 300
    )
    ggplot2::ggsave(
      file.path("figs", paste0("qq_", asset, ".png")),
      plot_qq(d$log_return, label),
      width = 5.5, height = 5.5, dpi = 300
    )
    cli::cli_alert_success("Figures saved for {label}")
  })
