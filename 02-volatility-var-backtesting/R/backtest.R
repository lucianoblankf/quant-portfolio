# VaR backtests: Kupiec, Christoffersen, conditional coverage, Basel traffic light.
# `hits` is a 0/1 vector of VaR breaches; `p` the expected breach probability (1 - alpha).

#' Kupiec proportion-of-failures test (unconditional coverage).
kupiec_pof <- function(hits, p) {
  n <- length(hits)
  x <- sum(hits)
  ll0 <- (n - x) * log(1 - p) + x * log(p)
  phat <- x / n
  ll1 <- dplyr::case_when(
    x == 0 ~ n * log(1 - phat),
    x == n ~ n * log(phat),
    .default = (n - x) * log(1 - phat) + x * log(phat)
  )
  lr <- -2 * (ll0 - ll1)
  tibble::tibble(
    breaches = x, rate = phat, lr = lr,
    p_value = stats::pchisq(lr, 1, lower.tail = FALSE)
  )
}

#' Christoffersen independence test: are breaches clustered in time?
christoffersen_ind <- function(hits) {
  h <- as.integer(hits)
  a <- h[-length(h)]
  b <- h[-1]
  n00 <- sum(a == 0 & b == 0)
  n01 <- sum(a == 0 & b == 1)
  n10 <- sum(a == 1 & b == 0)
  n11 <- sum(a == 1 & b == 1)
  pi01 <- n01 / (n00 + n01)
  pi11 <- if (n10 + n11 == 0) 0 else n11 / (n10 + n11)
  pi_all <- (n01 + n11) / (n00 + n01 + n10 + n11)
  xlogp <- function(x, p) if (x == 0) 0 else x * log(p)
  ll0 <- xlogp(n00 + n10, 1 - pi_all) + xlogp(n01 + n11, pi_all)
  ll1 <- xlogp(n00, 1 - pi01) + xlogp(n01, pi01) + xlogp(n10, 1 - pi11) + xlogp(n11, pi11)
  lr <- -2 * (ll0 - ll1)
  tibble::tibble(lr = lr, p_value = stats::pchisq(lr, 1, lower.tail = FALSE))
}

#' Backtest table from the long output of `rolling_var()`: one row per model and
#' confidence level with Kupiec, independence and conditional coverage p-values.
backtest_table <- function(rolling) {
  rolling |>
    dplyr::mutate(hit = as.integer(ret < -var)) |>
    dplyr::arrange(model, confidence, date) |>
    dplyr::group_by(model, confidence) |>
    dplyr::reframe({
      p <- 1 - confidence[1]
      kupiec <- kupiec_pof(hit, p)
      ind <- christoffersen_ind(hit)
      tibble::tibble(
        n = dplyr::n(),
        breaches = kupiec$breaches,
        expected = round(dplyr::n() * p, 1),
        rate = kupiec$rate,
        kupiec_p = kupiec$p_value,
        indep_p = ind$p_value,
        cond_cov_p = stats::pchisq(kupiec$lr + ind$lr, 2, lower.tail = FALSE)
      )
    })
}

#' Basel traffic light for 250 days of 99% VaR.
basel_zone <- function(breaches) {
  dplyr::case_when(breaches <= 4 ~ "green", breaches <= 9 ~ "yellow", .default = "red")
}
