# Plot helpers for project 1.

#' Histogram of returns against the fitted normal, on a log scale so tails are visible.
plot_histogram <- function(returns, label) {
  tibble::tibble(r = returns) |>
    ggplot2::ggplot(ggplot2::aes(r)) +
    ggplot2::geom_histogram(
      ggplot2::aes(y = ggplot2::after_stat(density)),
      bins = 120, fill = "#4C78A8", alpha = 0.75
    ) +
    ggplot2::stat_function(
      fun = stats::dnorm, args = list(mean = mean(returns), sd = stats::sd(returns)),
      colour = "#E45756", linewidth = 1
    ) +
    ggplot2::scale_y_log10(limits = c(1e-2, NA)) +
    ggplot2::labs(
      title = paste0(label, ": daily log returns vs the normal"),
      x = "Daily log return", y = "Density (log scale)"
    ) +
    ggplot2::theme_minimal()
}

#' QQ plot of standardised returns against the normal.
plot_qq <- function(returns, label) {
  tibble::tibble(observed = sort((returns - mean(returns)) / stats::sd(returns))) |>
    dplyr::mutate(theoretical = stats::qnorm(stats::ppoints(dplyr::n()))) |>
    ggplot2::ggplot(ggplot2::aes(theoretical, observed)) +
    ggplot2::geom_point(size = 0.6, colour = "#4C78A8") +
    ggplot2::geom_abline(colour = "#E45756") +
    ggplot2::coord_equal() +
    ggplot2::labs(
      title = paste0(label, ": QQ plot against the normal"),
      x = "Normal quantiles", y = "Observed quantiles (standardised)"
    ) +
    ggplot2::theme_minimal()
}
