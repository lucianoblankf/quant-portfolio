# 03: Taylor rule (static and dynamic) with HAC errors, Taylor principle, stability.

source("R/taylor.R")
source("R/tables.R")

cli::cli_h1("03 Taylor rule")

dataset <- readRDS("data/processed/dataset.rds") |>
  tidyr::drop_na(selic_l1)

static_rule <- stats::lm(selic ~ ipca12 + gap, data = dataset)
dynamic_rule <- stats::lm(selic ~ ipca12 + gap + selic_l1, data = dataset)
saveRDS(dynamic_rule, "data/processed/dynamic_rule.rds")

# Regression table (LaTeX and HTML) with HAC standard errors
models <- list(static_rule, dynamic_rule)
hac_se <- purrr::map(models, \(m) sqrt(diag(hac_vcov(m))))
hac_p <- purrr::map(models, \(m) lmtest::coeftest(m, vcov. = hac_vcov(m))[, 4])
dir.create("tabs", showWarnings = FALSE)
texreg::texreg(
  models,
  custom.model.names = c("Static", "Dynamic"),
  override.se = hac_se, override.pvalues = hac_p,
  custom.note = "HAC (Newey-West, 6 lags) standard errors in parentheses.",
  file = "tabs/taylor_rule.tex"
)
texreg::htmlreg(
  models,
  custom.model.names = c("Static", "Dynamic"),
  override.se = hac_se, override.pvalues = hac_p,
  custom.note = "HAC (Newey-West, 6 lags) standard errors in parentheses.",
  file = "tabs/taylor_rule.html"
)

coefficients <- dplyr::bind_rows(
  dplyr::mutate(tidy_hac(static_rule), model = "static", .before = 1),
  dplyr::mutate(tidy_hac(dynamic_rule), model = "dynamic", .before = 1)
)
save_table(coefficients, "taylor_coefficients", digits = 4)
cli::cli_h2("Taylor rule coefficients (HAC)")
print(round_numeric(coefficients, 4))

# Long-run response and the Taylor principle (long-run inflation coefficient = 1)
b <- stats::coef(dynamic_rule)
rho <- b[["selic_l1"]]
wald <- car::linearHypothesis(dynamic_rule, "ipca12 + selic_l1 = 1", vcov. = hac_vcov(dynamic_rule))
long_run <- tibble::tibble(
  rho = rho,
  inflation_lr = b[["ipca12"]] / (1 - rho),
  gap_lr = b[["gap"]] / (1 - rho),
  r2 = summary(dynamic_rule)$r.squared,
  taylor_principle_p = wald[2, ncol(wald)],
  residual_ar1 = stats::acf(stats::resid(dynamic_rule), plot = FALSE)$acf[2]
)
save_table(long_run, "long_run", digits = 3)
cli::cli_h2("Smoothing, long-run response, Taylor principle")
print(round_numeric(long_run, 3), width = Inf)

# Stability: sub-samples, Bai-Perron breakpoints, supF
subsamples <- dplyr::bind_rows(
  taylor_subsample(dplyr::filter(dataset, date < as.Date("2016-01-01")), "2003-2015"),
  taylor_subsample(dplyr::filter(dataset, date >= as.Date("2016-01-01")), "2016-2026")
)
save_table(subsamples, "taylor_subsamples", digits = 3)
cli::cli_h2("Taylor rule by sub-period")
print(round_numeric(subsamples, 3))

rule_formula <- selic ~ ipca12 + gap + selic_l1
breaks <- strucchange::breakpoints(rule_formula, data = dataset, h = 0.15)
supf <- strucchange::sctest(rule_formula, data = dataset, type = "supF", from = 0.15)
stability <- tibble::tibble(
  breakpoints = paste(dataset$date[breaks$breakpoints], collapse = ", "),
  supf_stat = unname(supf$statistic),
  supf_p = supf$p.value
)
save_table(stability, "structural_stability", digits = 4)
cli::cli_alert_info("Bai-Perron breakpoints: {stability$breakpoints}")
cli::cli_alert_info("supF = {round(stability$supf_stat, 1)}, p = {signif(stability$supf_p, 3)}")
