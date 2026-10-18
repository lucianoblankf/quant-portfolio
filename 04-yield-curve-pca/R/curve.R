# Raw Tesouro Direto data and the constant-maturity zero curve.

tesouro_url <- function() {
  paste0(
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/",
    "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
  )
}

#' Download the raw Tesouro Direto file once. Never overwrites an existing raw file.
download_raw_tesouro <- function(path = "data/raw/tesouro_direto.csv") {
  if (file.exists(path)) {
    cli::cli_alert_info("Raw file already exists, not downloading: {.path {path}}")
    return(invisible(path))
  }
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  utils::download.file(tesouro_url(), path, mode = "wb", quiet = TRUE)
  cli::cli_alert_success("Raw file saved to {.path {path}}")
  invisible(path)
}

#' Read the LTN (Tesouro Prefixado) records with clean names and a yield and
#' time-to-maturity (years) column.
read_ltn <- function(path = "data/raw/tesouro_direto.csv") {
  readr::read_delim(
    path,
    delim = ";",
    locale = readr::locale(decimal_mark = ",", date_format = "%d/%m/%Y"),
    col_types = readr::cols(
      `Data Vencimento` = readr::col_date(),
      `Data Base` = readr::col_date(),
      .default = readr::col_guess()
    )
  ) |>
    janitor::clean_names() |>
    dplyr::filter(tipo_titulo == "Tesouro Prefixado") |>
    dplyr::transmute(
      date = data_base,
      maturity = data_vencimento,
      ttm = as.numeric(maturity - date) / 365.25,
      yield = taxa_compra_manha / 100
    )
}

#' Constant-maturity zero curve: for each date, linear interpolation of yield between the
#' two bonds around each tenor. Days where the bonds do not bracket all tenors are dropped.
build_constant_maturity_curve <- function(ltn, tenors = c(1, 2, 3, 5)) {
  ltn |>
    dplyr::arrange(date, ttm) |>
    dplyr::group_by(date) |>
    dplyr::filter(dplyr::n() >= 3, min(ttm) <= min(tenors), max(ttm) >= max(tenors)) |>
    dplyr::reframe(
      tenor = tenors,
      yield = stats::approx(ttm, yield, xout = tenors)$y
    ) |>
    tidyr::pivot_wider(
      names_from = tenor, values_from = yield, names_glue = "y{tenor}y"
    )
}
