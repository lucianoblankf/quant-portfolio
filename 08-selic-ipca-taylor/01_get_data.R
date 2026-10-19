# 01: download the BCB SGS series once and build the monthly dataset.

source("R/data.R")
source("R/var_tools.R")

cli::cli_h1("01 Data")

series <- sgs_series()
purrr::walk(series$id, download_sgs)

dataset <- purrr::map2(series$id, series$name, read_sgs) |>
  purrr::reduce(dplyr::inner_join, by = "date") |>
  tidyr::drop_na() |>
  dplyr::arrange(date) |>
  dplyr::mutate(
    log_ibc = log(ibc),
    gap = 100 * (log_ibc - hp_trend(log_ibc)),   # output gap, % of the two-sided HP trend
    selic_l1 = dplyr::lag(selic)
  )

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
saveRDS(dataset, "data/processed/dataset.rds")

cli::cli_alert_success(
  "Monthly sample: {nrow(dataset)} observations, {min(dataset$date)} to {max(dataset$date)}"
)
