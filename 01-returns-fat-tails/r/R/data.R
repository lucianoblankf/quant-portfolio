# Data helpers: download and read the raw price file.

#' Asset labels used in tables and figures.
asset_labels <- function() {
  tibble::tibble(
    asset = c("ibovespa", "usd_brl"),
    label = c("Ibovespa", "USD/BRL"),
    ticker = c("^BVSP", "BRL=X")
  )
}

#' Download daily closing prices from Yahoo Finance and save them as the raw file.
#' The raw file is only written when it does not exist yet.
download_raw_prices <- function(path = "data/raw/prices.csv", start = "2010-01-01") {
  if (file.exists(path)) {
    cli::cli_alert_info("Raw file already exists, not downloading: {.path {path}}")
    return(invisible(path))
  }

  labels <- asset_labels()
  prices <- purrr::map2(labels$ticker, labels$label, \(ticker, label) {
    xts_obj <- suppressWarnings(
      quantmod::getSymbols(ticker, src = "yahoo", from = start, auto.assign = FALSE)
    )
    tibble::tibble(date = zoo::index(xts_obj), close = as.numeric(quantmod::Cl(xts_obj))) |>
      dplyr::rename(!!label := close)
  }) |>
    purrr::reduce(dplyr::full_join, by = "date")

  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  readr::write_csv(prices, path)
  cli::cli_alert_success("Raw prices saved to {.path {path}}")
  invisible(path)
}

#' Read the raw prices with sanitised column names (date, ibovespa, usd_brl).
read_raw_prices <- function(path = "data/raw/prices.csv") {
  readr::read_csv(path, show_col_types = FALSE, name_repair = "minimal") |>
    janitor::clean_names()
}
