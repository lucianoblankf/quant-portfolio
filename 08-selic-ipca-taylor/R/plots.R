# Plot helpers for project 8.

plot_selic_ipca <- function(data) {
  data |>
    dplyr::select(date, `Selic (% a.a.)` = selic, `IPCA 12m (%)` = ipca12) |>
    tidyr::pivot_longer(-date, names_to = "series", values_to = "value") |>
    ggplot2::ggplot(ggplot2::aes(date, value, colour = series)) +
    ggplot2::geom_line(linewidth = 0.7) +
    ggplot2::scale_colour_manual(values = c("#E45756", "#4C78A8")) +
    ggplot2::labs(title = "Selic and 12-month inflation", x = NULL, y = "%", colour = NULL) +
    ggplot2::theme_minimal() +
    ggplot2::theme(legend.position = "bottom")
}

plot_taylor_fit <- function(data, fitted_values) {
  data |>
    dplyr::mutate(fitted = fitted_values) |>
    ggplot2::ggplot(ggplot2::aes(date)) +
    ggplot2::geom_line(ggplot2::aes(y = selic, colour = "Actual Selic")) +
    ggplot2::geom_line(ggplot2::aes(y = fitted, colour = "Taylor rule (dynamic)"), linetype = 2) +
    ggplot2::scale_colour_manual(values = c("black", "#E45756")) +
    ggplot2::labs(title = "Selic: actual vs dynamic Taylor rule", x = NULL, y = "% a.a.", colour = NULL) +
    ggplot2::theme_minimal() +
    ggplot2::theme(legend.position = "bottom")
}

plot_irf <- function(irf_table) {
  ggplot2::ggplot(irf_table, ggplot2::aes(horizon, response)) +
    ggplot2::geom_ribbon(ggplot2::aes(ymin = lo, ymax = hi), fill = "#4C78A8", alpha = 0.25) +
    ggplot2::geom_line(colour = "#4C78A8", linewidth = 1) +
    ggplot2::geom_hline(yintercept = 0, linetype = 2) +
    ggplot2::facet_wrap(~variable, scales = "free_y") +
    ggplot2::labs(
      title = "Response to a one-s.d. Selic shock (90% bootstrap bands)",
      x = "Months after the shock", y = NULL
    ) +
    ggplot2::theme_minimal()
}
