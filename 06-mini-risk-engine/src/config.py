"""Parameters shared by the scripts (edit here, no command-line arguments)."""

# Risk factors: Yahoo tickers for stocks and FX (names are the factor names)
TICKERS = {"PETR4.SA": "petr4", "VALE3.SA": "vale3", "ITUB4.SA": "itub4", "WEGE3.SA": "wege3", "BRL=X": "usdbrl"}
PRICE_START = "2015-01-01"
BOND_TENOR_YEARS = 3.0  # rate factor: 3-year zero rate interpolated between LTNs

# Portfolio in R$ (held fixed at today's weights over the whole history)
EQUITY = {"petr4": 250_000, "vale3": 200_000, "itub4": 200_000, "wege3": 100_000}
FX = {"usdbrl": 150_000}
BOND_VALUE = 300_000

# Risk measures
ALPHAS = (0.95, 0.99)
HIST_WINDOW = 500
EWMA_LAMBDA = 0.94
MC_NU = 5            # Student-t degrees of freedom for the Monte Carlo
MC_SIMULATIONS = 200_000
SEED_MONTE_CARLO = 0

# Backtest
BACKTEST_ALPHA = 0.99
BACKTEST_WINDOW = 500
