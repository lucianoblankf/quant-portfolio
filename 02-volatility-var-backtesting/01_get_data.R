# 01: raw Ibovespa prices (downloaded once) and processed log returns.

cli::cli_h1("01 Data")

raw_path <- "data/raw/prices.csv"

if (!file.exists(raw_path)) {
  cli::cli_alert_info("Downloading Ibovespa from Yahoo Finance")
  ibov <- suppressWarnings(
    quantmod::getSymbols("^BVSP", src = "yahoo", from = "2010-01-01", auto.assign = FALSE)
  )
  dir.create("data/raw", showWarnings = FALSE, recursive = TRUE)
  tibble::tibble(Date = zoo::index(ibov), Ibovespa = as.numeric(quantmod::Cl(ibov))) |>
    readr::write_csv(raw_path)
}

returns <- readr::read_csv(raw_path, show_col_types = FALSE, name_repair = "minimal") |>
  janitor::clean_names() |>
  dplyr::select(date, ibovespa) |>
  tidyr::drop_na(ibovespa) |>
  dplyr::arrange(date) |>
  dplyr::mutate(log_return = c(NA_real_, diff(log(ibovespa)))) |>
  tidyr::drop_na(log_return)

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
saveRDS(returns, "data/processed/returns.rds")

cli::cli_alert_success(
  "{nrow(returns)} Ibovespa returns, {min(returns$date)} to {max(returns$date)}"
)
