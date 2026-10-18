# 03: trade the selected pairs out of sample with fixed formation hedge ratios.

source("R/pairs.R")
source("R/tables.R")

cli::cli_h1("03 Backtest")

config <- pairs_config()
prices <- readRDS("data/processed/prices.rds")
selected <- readRDS("data/processed/selected_pairs.rds")

trading <- prices |>
  dplyr::filter(date >= config$formation_end) |>
  dplyr::mutate(dplyr::across(-date, log))

results <- selected |>
  purrr::pmap(\(y, x, beta, ...) {
    bt <- backtest_pair(trading$date, trading[[y]], trading[[x]], beta, config)
    bt$pair <- paste(toupper(y), toupper(x), sep = "/")
    bt
  })

pair_perf <- results |>
  purrr::map(\(bt) dplyr::bind_cols(tibble::tibble(pair = bt$pair), perf_stats(bt$daily$ret, bt$trades, bt$wins))) |>
  purrr::list_rbind()
save_table(pair_perf, "performance")

portfolio <- results |>
  purrr::map(\(bt) dplyr::select(bt$daily, date, ret)) |>
  purrr::list_rbind() |>
  dplyr::summarise(ret = mean(ret), .by = date) |>
  dplyr::arrange(date)
saveRDS(portfolio, "data/processed/portfolio_returns.rds")

portfolio_perf <- perf_stats(portfolio$ret, sum(pair_perf$trades), sum(pair_perf$wins))
save_table(portfolio_perf, "portfolio_performance")

sub_period <- function(label, from, to) {
  d <- portfolio |> dplyr::filter(dplyr::between(date, as.Date(from), as.Date(to)))
  perf_stats(d$ret) |>
    dplyr::select(ann_return, ann_vol, sharpe) |>
    dplyr::mutate(period = label, .before = 1)
}
portfolio_sub <- dplyr::bind_rows(
  sub_period("2020-2021", "2020-01-01", "2021-12-31"),
  sub_period("2022-2023", "2022-01-01", "2023-12-31"),
  sub_period("2024-", "2024-01-01", "2099-01-01")
)
save_table(portfolio_sub, "portfolio_by_period")

cli::cli_h2("Performance by pair (entry |z| > 2, exit |z| < 0.5, stop |z| > 4, 10 bp per side)")
print(round_numeric(pair_perf, 3), width = Inf)
cli::cli_h2("Equal-weight portfolio")
print(round_numeric(portfolio_perf, 3), width = Inf)
cli::cli_h2("Portfolio by sub-period")
print(round_numeric(portfolio_sub, 3))
