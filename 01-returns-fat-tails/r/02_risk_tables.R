# 02: descriptive statistics, Jarque-Bera, VaR / ES tables and worst days.

source("R/data.R")
source("R/risk.R")

cli::cli_h1("02 Risk tables")

returns <- readRDS("data/processed/returns.rds")
labels <- asset_labels()
dir.create("tabs", showWarnings = FALSE)

by_asset <- returns |>
  dplyr::group_by(asset) |>
  dplyr::group_split()

stats_tbl <- by_asset |>
  purrr::map(\(d) dplyr::bind_cols(tibble::tibble(asset = d$asset[1]), summarise_returns(d$log_return))) |>
  purrr::list_rbind()

var_tbl <- by_asset |>
  purrr::map(\(d) dplyr::bind_cols(tibble::tibble(asset = d$asset[1]), var_table(d$log_return))) |>
  purrr::list_rbind()

worst_days <- returns |>
  dplyr::group_by(asset) |>
  dplyr::slice_min(log_return, n = 5, with_ties = FALSE) |>
  dplyr::ungroup() |>
  dplyr::arrange(asset, log_return)

purrr::walk2(
  list(stats_tbl, var_tbl, worst_days),
  c("stats", "var", "worst_days"),
  \(tbl, name) {
    saveRDS(tbl, file.path("tabs", paste0(name, ".rds")))
    readr::write_csv(tbl, file.path("tabs", paste0(name, ".csv")))
    knitr::kable(tbl, format = "latex", digits = 4, booktabs = TRUE) |>
      writeLines(file.path("tabs", paste0(name, ".tex")))
  }
)

cli::cli_h2("Descriptive statistics")
print(stats_tbl |> dplyr::mutate(dplyr::across(where(is.numeric), \(x) round(x, 4))), width = Inf)

cli::cli_h2("1-day VaR and ES")
print(var_tbl |> dplyr::mutate(dplyr::across(where(is.numeric), \(x) round(x, 4))), width = Inf)

cli::cli_h2("Five worst days")
worst_days |>
  dplyr::left_join(labels, by = "asset") |>
  dplyr::group_by(label) |>
  dplyr::summarise(days = paste0(date, " (", sprintf("%+.1f%%", 100 * log_return), ")", collapse = ", ")) |>
  purrr::pmap(\(label, days) cli::cli_bullets(c("*" = "{label}: {days}")))

cli::cli_alert_success("Tables saved to {.path tabs/}")
