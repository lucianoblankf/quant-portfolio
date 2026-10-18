# 04: Kupiec / Christoffersen backtests, Basel traffic light, 2020 breaches.

source("R/var_models.R")
source("R/backtest.R")
source("R/tables.R")

cli::cli_h1("04 Backtest")

rolling <- readRDS("data/processed/rolling_var.rds")
labels <- model_labels()

backtest <- backtest_table(rolling) |>
  dplyr::mutate(model = labels[model]) |>
  dplyr::arrange(confidence, match(model, labels))
save_table(backtest, "backtest")
cli::cli_h2("Backtest (Kupiec = unconditional coverage; indep = Christoffersen)")
print(round_numeric(backtest, 3), n = Inf, width = Inf)

basel <- rolling |>
  dplyr::filter(confidence == 0.99) |>
  dplyr::slice_max(date, n = 250, by = model) |>
  dplyr::summarise(breaches = sum(ret < -var), .by = model) |>
  dplyr::mutate(model = labels[model], zone = basel_zone(breaches))
save_table(basel, "basel_traffic_light")
cli::cli_h2("Basel traffic light, last 250 days, 99% VaR")
print(basel)

covid_2020 <- rolling |>
  dplyr::filter(confidence == 0.99, format(date, "%Y") == "2020") |>
  dplyr::summarise(days = dplyr::n(), breaches = sum(ret < -var), .by = model) |>
  dplyr::mutate(model = labels[model])
save_table(covid_2020, "breaches_2020")
cli::cli_h2("Breaches of the 99% VaR in 2020")
print(covid_2020)
