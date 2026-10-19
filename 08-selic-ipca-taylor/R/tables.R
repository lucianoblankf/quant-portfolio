# Helpers to export result tables to tabs/ as .rds, .csv and .tex.

save_table <- function(tbl, name, dir = "tabs", digits = 4) {
  dir.create(dir, showWarnings = FALSE, recursive = TRUE)
  saveRDS(tbl, file.path(dir, paste0(name, ".rds")))
  readr::write_csv(tbl, file.path(dir, paste0(name, ".csv")))
  knitr::kable(tbl, format = "latex", digits = digits, booktabs = TRUE) |>
    writeLines(file.path(dir, paste0(name, ".tex")))
  invisible(tbl)
}

#' Round every numeric column for console display.
round_numeric <- function(tbl, digits = 4) {
  dplyr::mutate(tbl, dplyr::across(where(is.numeric), \(x) round(x, digits)))
}
