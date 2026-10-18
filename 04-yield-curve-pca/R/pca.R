# PCA of weekly yield changes, factor stress scenarios and reconstruction error.

#' Weekly (last observation of each ISO week) yield changes in basis points, plus simple
#' level / slope / curvature changes. Changes spanning a gap above `max_gap_days` are dropped.
weekly_changes <- function(curve, max_gap_days = 10) {
  curve |>
    dplyr::mutate(week = format(date, "%G-%V")) |>
    dplyr::slice_tail(n = 1, by = week) |>
    dplyr::arrange(date) |>
    dplyr::mutate(
      gap_days = as.numeric(date - dplyr::lag(date)),
      level = (y1y + y2y + y3y + y5y) / 4,
      slope = y5y - y1y,
      curvature = 2 * y2y - y1y - y3y,
      dplyr::across(c(y1y, y2y, y3y, y5y, level, slope, curvature), \(x) (x - dplyr::lag(x)) * 1e4)
    ) |>
    dplyr::filter(!is.na(gap_days), gap_days <= max_gap_days) |>
    dplyr::select(date, y1y, y2y, y3y, y5y, level, slope, curvature)
}

#' Covariance PCA of the yield changes with the usual sign conventions:
#' PC1 up = all rates up, PC2 up = long end up against the short end,
#' PC3 up = belly above the wings.
yield_pca <- function(changes, yield_cols = c("y1y", "y2y", "y3y", "y5y")) {
  pca <- stats::prcomp(changes[yield_cols], center = TRUE, scale. = FALSE)
  loadings <- pca$rotation
  scores <- pca$x

  flip <- function(j) {
    loadings[, j] <<- -loadings[, j]
    scores[, j] <<- -scores[, j]
  }
  k <- length(yield_cols)
  if (sum(loadings[, 1]) < 0) flip(1)
  if (loadings[k, 2] < loadings[1, 2]) flip(2)
  if (mean(loadings[2:3, 3]) < mean(loadings[c(1, k), 3])) flip(3)

  list(
    sdev = pca$sdev,
    center = pca$center,
    loadings = loadings,
    scores = scores,
    var_explained = pca$sdev^2 / sum(pca$sdev^2),
    yield_cols = yield_cols
  )
}

#' Variance explained by each component as a tidy table.
variance_table <- function(fit) {
  tibble::tibble(
    factor = paste0("PC", seq_along(fit$sdev)),
    share = fit$var_explained,
    cumulative = cumsum(fit$var_explained),
    weekly_sd_bp = fit$sdev
  )
}

#' Loadings as a tidy table (one row per tenor).
loadings_table <- function(fit) {
  tibble::as_tibble(fit$loadings, rownames = "tenor")
}

#' Correlation of each PC score with the simple level, slope and curvature changes.
factor_correlations <- function(fit, changes) {
  tibble::tibble(
    factor = c("PC1 vs level", "PC2 vs slope", "PC3 vs curvature"),
    correlation = c(
      stats::cor(fit$scores[, 1], changes$level),
      stats::cor(fit$scores[, 2], changes$slope),
      stats::cor(fit$scores[, 3], changes$curvature)
    )
  )
}

#' Share of variance explained in two sub-periods.
subperiod_table <- function(changes, split_date = as.Date("2019-01-01")) {
  changes |>
    dplyr::mutate(period = dplyr::if_else(date < split_date, "before_2019", "from_2019")) |>
    dplyr::group_split(period) |>
    purrr::map(\(d) {
      p <- stats::prcomp(d[c("y1y", "y2y", "y3y", "y5y")], center = TRUE, scale. = FALSE)
      share <- p$sdev^2 / sum(p$sdev^2)
      tibble::tibble(
        period = d$period[1], n = nrow(d), weekly_sd_bp_pc1 = p$sdev[1],
        pc1 = share[1], pc2 = share[2], pc3 = share[3]
      )
    }) |>
    purrr::list_rbind()
}

#' Stress scenarios: shift the latest curve by +/- `k` standard deviations of each of the
#' first three factors and revalue a zero-coupon bond at each tenor with fixed maturity:
#' return = (1 + y_old)^t / (1 + y_new)^t - 1.
pc_stress <- function(fit, last_yields, tenors = c(1, 2, 3, 5), shocks = c(-3, 3)) {
  tidyr::expand_grid(factor_id = 1:3, shock_sd = shocks) |>
    purrr::pmap(\(factor_id, shock_sd) {
      shift_bp <- shock_sd * fit$sdev[factor_id] * fit$loadings[, factor_id]
      y_new <- last_yields + shift_bp / 1e4
      ret_pct <- 100 * ((1 + last_yields)^tenors / (1 + y_new)^tenors - 1)
      tibble::tibble(
        factor = paste0("PC", factor_id), shock_sd = shock_sd, tenor = tenors,
        shift_bp = as.numeric(shift_bp), return_pct = as.numeric(ret_pct)
      )
    }) |>
    purrr::list_rbind()
}

#' RMSE (bp) of the weekly changes rebuilt from the first k factors.
reconstruction_rmse <- function(fit, changes) {
  x <- as.matrix(sweep(as.matrix(changes[fit$yield_cols]), 2, fit$center))
  purrr::map(seq_along(fit$sdev), \(k) {
    approx_x <- fit$scores[, 1:k, drop = FALSE] %*% t(fit$loadings[, 1:k, drop = FALSE])
    tibble::tibble(k = k, rmse_bp = sqrt(mean((x - approx_x)^2)))
  }) |>
    purrr::list_rbind()
}
