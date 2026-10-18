# Plot helpers for project 7.

plot_spread <- function(dates, y, x, beta, y_name, x_name, formation_end) {
  tibble::tibble(date = dates, spread = y - beta * x) |>
    dplyr::mutate(window = dplyr::if_else(date < formation_end, "Formation", "Trading")) |>
    ggplot2::ggplot(ggplot2::aes(date, spread, colour = window)) +
    ggplot2::geom_line(linewidth = 0.4) +
    ggplot2::geom_vline(xintercept = formation_end, linetype = 2) +
    ggplot2::scale_colour_manual(values = c("#4C78A8", "#E45756")) +
    ggplot2::labs(
      title = sprintf("Spread %s / %s with the formation hedge ratio (%.2f)", y_name, x_name, beta),
      subtitle = "Stationary in formation, then it drifts: cointegration did not hold out of sample",
      x = NULL, y = "log(Y) - beta * log(X)", colour = NULL
    ) +
    ggplot2::theme_minimal()
}

plot_equity <- function(portfolio) {
  portfolio |>
    dplyr::mutate(equity = cumprod(1 + ret)) |>
    ggplot2::ggplot(ggplot2::aes(date, equity)) +
    ggplot2::geom_line(colour = "#4C78A8") +
    ggplot2::geom_hline(yintercept = 1, linetype = 2, colour = "grey50") +
    ggplot2::labs(
      title = "Equal-weight portfolio of selected pairs, out of sample (after costs)",
      x = NULL, y = "Growth of 1"
    ) +
    ggplot2::theme_minimal()
}

plot_adf_scan <- function(scan, critical_value) {
  ggplot2::ggplot(scan, ggplot2::aes(adf)) +
    ggplot2::geom_histogram(bins = 30, fill = "#4C78A8") +
    ggplot2::geom_vline(xintercept = critical_value, colour = "#E45756", linetype = 2) +
    ggplot2::labs(
      title = "Engle-Granger statistics for all pairs (formation window)",
      subtitle = "Red line: 5% critical value",
      x = "ADF statistic of the residual", y = "Pairs"
    ) +
    ggplot2::theme_minimal()
}
