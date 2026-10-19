# 02: unit-root tests (ADF: H0 unit root; KPSS: H0 stationary).

source("R/taylor.R")
source("R/tables.R")

cli::cli_h1("02 Stationarity")

dataset <- readRDS("data/processed/dataset.rds")

unit_roots <- dplyr::bind_rows(
  unit_root_tests(dataset$selic, "selic"),
  unit_root_tests(dataset$ipca12, "ipca12"),
  unit_root_tests(dataset$gap, "gap"),
  unit_root_tests(diff(dataset$selic), "d_selic"),
  unit_root_tests(diff(dataset$ipca12), "d_ipca12")
)
save_table(unit_roots, "unit_roots", digits = 3)
print(round_numeric(unit_roots, 3))
