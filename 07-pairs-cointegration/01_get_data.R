# 01: raw adjusted prices of Brazilian stocks (downloaded once) and processed log prices.

cli::cli_h1("01 Data")

raw_path <- "data/raw/prices.csv"
tickers <- c(
  "PETR3", "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "GGBR4", "GOAU4", "ELET3", "ELET6",
  "CMIG4", "CPLE6", "ABEV3", "WEGE3", "SUZB3", "CSNA3", "USIM5", "BRFS3"
)

if (!file.exists(raw_path)) {
  cli::cli_alert_info("Downloading {length(tickers)} tickers from Yahoo Finance")
  prices <- purrr::map(tickers, \(ticker) {
    x <- tryCatch(
      suppressWarnings(
        quantmod::getSymbols(paste0(ticker, ".SA"), src = "yahoo", from = "2015-01-01", auto.assign = FALSE)
      ),
      error = \(e) NULL
    )
    if (is.null(x)) {
      cli::cli_alert_warning("{ticker}: download failed, dropped")
      return(NULL)
    }
    tibble::tibble(date = zoo::index(x), close = as.numeric(quantmod::Ad(x))) |>
      dplyr::rename(!!ticker := close)
  }) |>
    purrr::compact() |>
    purrr::reduce(dplyr::full_join, by = "date")
  dir.create("data/raw", showWarnings = FALSE, recursive = TRUE)
  readr::write_csv(prices, raw_path)
}

prices <- readr::read_csv(raw_path, show_col_types = FALSE) |>
  janitor::clean_names() |>
  dplyr::arrange(date) |>
  tidyr::drop_na()

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
saveRDS(prices, "data/processed/prices.rds")

cli::cli_alert_success(
  "{ncol(prices) - 1} stocks, {nrow(prices)} days ({min(prices$date)} to {max(prices$date)})"
)
