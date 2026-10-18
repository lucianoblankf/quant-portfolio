# Plot helpers for project 4.

plot_curve_history <- function(curve) {
  curve |>
    tidyr::pivot_longer(-date, names_to = "tenor", values_to = "yield") |>
    dplyr::mutate(tenor = factor(tenor, levels = c("y1y", "y2y", "y3y", "y5y"), labels = c("1y", "2y", "3y", "5y"))) |>
    ggplot2::ggplot(ggplot2::aes(date, yield, colour = tenor)) +
    ggplot2::geom_line(linewidth = 0.5) +
    ggplot2::scale_y_continuous(labels = scales::percent) +
    ggplot2::labs(
      title = "Constant-maturity pre-fixed zero curve",
      x = NULL, y = "Yield (a.a.)", colour = "Tenor"
    ) +
    ggplot2::theme_minimal()
}

plot_loadings <- function(loadings) {
  loadings |>
    dplyr::select(tenor, PC1, PC2, PC3) |>
    tidyr::pivot_longer(-tenor, names_to = "factor", values_to = "loading") |>
    dplyr::mutate(tenor = factor(tenor, levels = c("y1y", "y2y", "y3y", "y5y"), labels = c("1y", "2y", "3y", "5y"))) |>
    ggplot2::ggplot(ggplot2::aes(tenor, loading, colour = factor, group = factor)) +
    ggplot2::geom_line(linewidth = 1) +
    ggplot2::geom_point(size = 2) +
    ggplot2::geom_hline(yintercept = 0, linetype = 2, colour = "grey50") +
    ggplot2::scale_colour_manual(
      values = c("#4C78A8", "#F58518", "#54A24B"),
      labels = c("PC1 (level)", "PC2 (slope)", "PC3 (curvature)")
    ) +
    ggplot2::labs(title = "Principal-component loadings", x = "Tenor", y = "Loading", colour = NULL) +
    ggplot2::theme_minimal()
}

plot_scree <- function(variance) {
  ggplot2::ggplot(variance, ggplot2::aes(factor, share)) +
    ggplot2::geom_col(fill = "#4C78A8") +
    ggplot2::geom_text(ggplot2::aes(label = scales::percent(share, 0.1)), vjust = -0.4) +
    ggplot2::scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
    ggplot2::labs(
      title = "Share of weekly yield-change variance by factor", x = NULL, y = NULL
    ) +
    ggplot2::theme_minimal()
}
