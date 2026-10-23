"""Parameters shared by the scripts (edit here, no command-line arguments)."""

# Reference option: at the money, one year, 5% rate, 20% volatility
S, K, T, R, SIG = 100.0, 100.0, 1.0, 0.05, 0.20

# Seeds (every stochastic step is reproducible)
SEED_MONTE_CARLO = 11
SEED_HEDGING = 5

# Monte Carlo and binomial grids
MC_SIZES = (1_000, 10_000, 100_000, 1_000_000)
TREE_STEPS = (10, 25, 50, 100, 250, 500, 1000, 2000)

# Delta hedging
REBALANCES = (4, 12, 26, 52, 126, 252)
HEDGE_VOLS = (0.10, 0.15, 0.20, 0.25, 0.30)
HEDGE_PATHS = 20_000
HEDGE_DRIFT = 0.10

# Real smile: SPY expiry closest to this many days, approximate dividend yield
SMILE_TICKER = "SPY"
SMILE_DAYS = 35
SMILE_DIVIDEND_YIELD = 0.013
