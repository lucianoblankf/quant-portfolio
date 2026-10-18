# Cointegration and pairs-trading functions for project 7.

#' Design constants shared by the scripts.
pairs_config <- function() {
  list(
    formation_end = as.Date("2020-01-01"),  # formation: before; trading: from this date
    adf_cv_5pct = -3.34,                    # MacKinnon (1991), 2 variables, with constant
    half_life_range = c(2, 60),
    n_selected = 6,
    entry = 2, exit = 0.5, stop = 4, lookback = 60,
    cost = 10 / 1e4                         # per side, on traded notional
  )
}

#' Half-life of mean reversion from an AR(1) on the spread:
#' ds_t = a + b * s_{t-1} + e, half-life = -ln(2) / ln(1 + b). Inf if it does not revert.
half_life <- function(spread) {
  ds <- diff(spread)
  lagged <- spread[-length(spread)]
  b <- unname(stats::coef(stats::lm(ds ~ lagged))[2])
  if (b >= 0) {
    return(Inf)
  }
  -log(2) / log(1 + b)
}

#' Engle-Granger two-step test: regress log Y on log X and test the residual for a unit
#' root. The ADF statistic of a residual does not follow the usual Dickey-Fuller
#' distribution: compare it with MacKinnon critical values (5%: -3.34, 1%: -3.90 for two
#' variables with a constant), not with `adf.test()`'s p-value.
engle_granger <- function(y, x) {
  fit <- stats::lm(y ~ x)
  e <- stats::residuals(fit)
  tibble::tibble(
    beta = unname(stats::coef(fit)[2]),
    alpha = unname(stats::coef(fit)[1]),
    adf = suppressWarnings(tseries::adf.test(e, k = 1)$statistic[[1]]),
    half_life = half_life(e)
  )
}

#' Engle-Granger statistics for every pair of columns of a matrix of log prices.
scan_pairs <- function(log_prices) {
  utils::combn(colnames(log_prices), 2, simplify = FALSE) |>
    purrr::map(\(p) {
      dplyr::bind_cols(
        tibble::tibble(y = p[1], x = p[2]),
        engle_granger(log_prices[, p[1]], log_prices[, p[2]])
      )
    }) |>
    purrr::list_rbind() |>
    dplyr::arrange(adf)
}

#' Trade the spread s = log Y - beta log X with a rolling z-score.
#'   z > entry -> short the spread; z < -entry -> long the spread;
#'   |z| < exit -> close; |z| > stop -> close (the relation broke).
#' The position on day t is decided with information up to t - 1 and earns the day-t
#' change. Returns are on gross exposure (1 + |beta|); the cost applies to every change in
#' position (the legs sum to the gross exposure).
backtest_pair <- function(dates, y, x, beta, config = pairs_config()) {
  y <- unname(y)
  x <- unname(x)
  n <- length(y)
  spread <- y - beta * x
  gross <- 1 + abs(beta)

  z <- rep(NA_real_, n)
  for (t in (config$lookback + 1):n) {
    window <- spread[(t - config$lookback):(t - 1)]
    z[t] <- (spread[t] - mean(window)) / stats::sd(window)
  }

  daily_pnl <- c(NA_real_, diff(y) - beta * diff(x))  # log P&L of one unit of the spread
  position <- numeric(n)
  ret <- numeric(n)
  current <- 0
  trades <- 0
  wins <- 0
  trade_pnl <- 0

  for (t in 2:n) {
    zt <- z[t - 1]
    new <- current
    if (!is.na(zt)) {
      if (current == 0) {
        if (zt > config$entry && zt < config$stop) {
          new <- -1
        } else if (zt < -config$entry && zt > -config$stop) {
          new <- 1
        }
      } else if (abs(zt) < config$exit || abs(zt) > config$stop) {
        new <- 0
      }
    }
    turnover <- abs(new - current)
    ret[t] <- new * daily_pnl[t] / gross - turnover * config$cost
    if (current != 0) {
      trade_pnl <- trade_pnl + ret[t]
    }
    if (new != current) {
      if (current != 0) {
        trades <- trades + 1
        wins <- wins + (trade_pnl > 0)
        trade_pnl <- 0
      }
      if (new != 0) {
        trade_pnl <- -turnover * config$cost
      }
    }
    current <- new
    position[t] <- current
  }

  list(
    daily = tibble::tibble(date = dates, ret = ret, position = position, z = z),
    trades = trades,
    wins = wins
  )
}

#' Performance statistics of a daily return series (one row).
perf_stats <- function(ret, trades = NA_real_, wins = NA_real_) {
  ret <- ret[!is.na(ret)]
  equity <- cumprod(1 + ret)
  tibble::tibble(
    ann_return = mean(ret) * 252,
    ann_vol = stats::sd(ret) * sqrt(252),
    sharpe = if (stats::sd(ret) > 0) mean(ret) / stats::sd(ret) * sqrt(252) else NA_real_,
    max_drawdown = min(equity / cummax(equity) - 1),
    total_return = utils::tail(equity, 1) - 1,
    trades = trades,
    wins = wins,
    hit_rate = if (is.na(trades) || trades == 0) NA_real_ else wins / trades
  )
}
