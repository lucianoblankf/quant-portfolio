# Plot helpers for project 2.

plot_acf_squared <- function(returns, max_lag = 30) {
  acf_values <- stats::acf(returns^2, lag.max = max_lag, plot = FALSE)$acf[-1]
  tibble::tibble(lag = seq_len(max_lag), acf = as.numeric(acf_values)) |>
    ggplot2::ggplot(ggplot2::aes(lag, acf)) +
    ggplot2::geom_col(fill = "#4C78A8") +
    ggplot2::geom_hline(
      yintercept = c(-1, 1) * 1.96 / sqrt(length(returns)),
      linetype = 2, colour = "#E45756"
    ) +
    ggplot2::labs(
      title = "Ibovespa: autocorrelation of squared returns",
      x = "Lag (days)", y = "ACF"
    ) +
    ggplot2::theme_minimal()
}

#' Realised returns against two 99% VaR forecasts over a window of dates.
plot_var_window <- function(rolling, from, to, models = c("hist", "garcht")) {
  labels <- model_labels()
  window <- rolling |>
    dplyr::filter(confidence == 0.99, dplyr::between(date, as.Date(from), as.Date(to)))
  ggplot2::ggplot() +
    ggplot2::geom_col(
      data = dplyr::distinct(window, date, ret),
      ggplot2::aes(date, ret), fill = "grey70", width = 1
    ) +
    ggplot2::geom_line(
      data = dplyr::filter(window, model %in% models) |>
        dplyr::mutate(model = labels[model]),
      ggplot2::aes(date, -var, colour = model), linewidth = 0.8
    ) +
    ggplot2::scale_colour_manual(values = c("#E45756", "#4C78A8")) +
    ggplot2::labs(
      title = "99% VaR through the COVID crash: historical vs GARCH-t",
      x = NULL, y = "Daily return / -VaR", colour = NULL
    ) +
    ggplot2::theme_minimal() +
    ggplot2::theme(legend.position = "bottom")
}

plot_garch_volatility <- function(rolling) {
  rolling |>
    dplyr::distinct(date, sigma_garcht) |>
    dplyr::mutate(ann_vol = sqrt(252) * sigma_garcht) |>
    ggplot2::ggplot(ggplot2::aes(date, ann_vol)) +
    ggplot2::geom_line(colour = "#4C78A8") +
    ggplot2::scale_y_continuous(labels = scales::percent) +
    ggplot2::labs(
      title = "GARCH-t annualised conditional volatility (out of sample)",
      x = NULL, y = "Volatility"
    ) +
    ggplot2::theme_minimal()
}
