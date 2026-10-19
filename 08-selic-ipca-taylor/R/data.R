# Banco Central do Brasil (SGS) data helpers.

#' SGS series used in the project: name, series id and description.
sgs_series <- function() {
  tibble::tibble(
    name = c("selic", "ipca12", "ibc", "fx"),
    id = c(4189, 13522, 24364, 3698),
    description = c(
      "Selic, % a.a., monthly average", "IPCA, 12-month change, %",
      "IBC-Br activity index, seasonally adjusted", "USD/BRL, end of month"
    )
  )
}

#' Download one SGS series once to data/raw/. Never overwrites an existing raw file.
download_sgs <- function(id, dir = "data/raw") {
  path <- file.path(dir, sprintf("sgs_%d.csv", id))
  if (file.exists(path)) {
    return(invisible(path))
  }
  url <- sprintf(
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.%d/dados?formato=json&dataInicial=01/01/2003&dataFinal=31/12/2026",
    id
  )
  dir.create(dir, showWarnings = FALSE, recursive = TRUE)
  readr::write_csv(jsonlite::fromJSON(url), path)
  cli::cli_alert_success("Downloaded series {id} to {.path {path}}")
  invisible(path)
}

#' Read one raw SGS file as a tibble (date, value) with the series name as column.
read_sgs <- function(id, name, dir = "data/raw") {
  readr::read_csv(file.path(dir, sprintf("sgs_%d.csv", id)), show_col_types = FALSE) |>
    janitor::clean_names() |>
    dplyr::transmute(date = as.Date(data, format = "%d/%m/%Y"), !!name := valor)
}
