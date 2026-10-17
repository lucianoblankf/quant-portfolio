# Cointegration and pairs-trading functions for project 7.

# Engle-Granger two-step test: regress log Y on log X, test the residual for a unit root.
# NOTE: the ADF statistic of a *residual* does not follow the usual Dickey-Fuller
# distribution; compare it with MacKinnon critical values (5%: -3.34, 1%: -3.90 for
# two variables with a constant), not with adf.test()'s p-value.
engle_granger <- function(y, x) {
  fit <- lm(y ~ x)
  e <- residuals(fit)
  list(beta = unname(coef(fit)[2]), alpha = unname(coef(fit)[1]),
       adf = suppressWarnings(tseries::adf.test(e, k = 1)$statistic[[1]]),
       half_life = half_life(e), resid = e)
}

# Half-life of mean reversion from an AR(1) on the spread: ds_t = a + b * s_{t-1} + e,
# half-life = -ln(2) / ln(1 + b). Returns Inf if the spread does not revert.
half_life <- function(s) {
  ds <- diff(s); lag <- s[-length(s)]
  b <- unname(coef(lm(ds ~ lag))[2])
  if (b >= 0) return(Inf)
  -log(2) / log(1 + b)
}

# Trade the spread s = log Y - beta log X with a rolling z-score.
#   z > entry   -> short the spread (short Y, long beta X)
#   z < -entry  -> long the spread
#   |z| < exit  -> close;  |z| > stop -> close (the relation broke)
# The position on day t is decided with information up to t-1 and earns the day-t change.
# Return is on gross exposure (1 + |beta|); transaction cost applies to every change in
# position, on both legs.
backtest_pair <- function(y, x, beta, dates, entry = 2, exit = 0.5, stop = 4, lookback = 60, cost = 0.001) {
  y <- unname(y); x <- unname(x); n <- length(y); s <- y - beta * x
  z <- rep(NA_real_, n)
  for (t in (lookback + 1):n) {
    w <- s[(t - lookback):(t - 1)]
    z[t] <- (s[t] - mean(w)) / sd(w)
  }
  pos <- numeric(n)        # position held DURING day t (decided on z[t-1])
  cur <- 0; trades <- 0; wins <- 0; entry_equity <- NA
  gross <- 1 + abs(beta)
  dret <- c(NA, diff(y) - beta * diff(x))     # daily log P&L of one unit of the spread
  ret <- numeric(n); cum_trade <- 0
  for (t in 2:n) {
    zt <- z[t - 1]
    new <- cur
    if (!is.na(zt)) {
      if (cur == 0) {
        if (zt > entry && zt < stop) new <- -1 else if (zt < -entry && zt > -stop) new <- 1
      } else if (abs(zt) < exit || abs(zt) > stop) new <- 0
    }
    turnover <- abs(new - cur)
    r <- new * dret[t] / gross - turnover * cost   # cost on the traded notional (legs sum to gross exposure)
    ret[t] <- r
    if (cur != 0) cum_trade <- cum_trade + r
    if (new != cur) {
      if (cur != 0) { trades <- trades + 1; wins <- wins + (cum_trade > 0); cum_trade <- 0 }
      if (new != 0) cum_trade <- -turnover * cost
    }
    cur <- new; pos[t] <- cur
  }
  list(ret = ret, pos = pos, z = z, trades = trades, wins = wins)
}

perf_stats <- function(ret, trades = NA, wins = NA) {
  ret <- ret[!is.na(ret)]
  eq <- cumprod(1 + ret)
  c(ann_return = mean(ret) * 252, ann_vol = sd(ret) * sqrt(252),
    sharpe = ifelse(sd(ret) > 0, mean(ret) / sd(ret) * sqrt(252), NA),
    max_drawdown = min(eq / cummax(eq) - 1), total_return = unname(tail(eq, 1) - 1),
    trades = unname(trades), wins = unname(wins),
    hit_rate = ifelse(is.na(trades) || trades == 0, NA, wins / trades))
}
