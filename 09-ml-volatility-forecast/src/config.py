"""Parameters shared by the scripts (edit here, no command-line arguments)."""

HORIZON = 5            # forecast the mean variance over the next 5 trading days
START_ROW = 750        # first forecast after 750 days of history
REFIT_EVERY = 63       # re-fit the models every 63 days (walk-forward, expanding window)

SEED = 0               # random_state of the tree models and the permutation importance

# Sub-periods used to report accuracy
COVID_START, COVID_END = "2020-02-15", "2020-06-30"

# Out-of-sample share used to fit the boosting model for the permutation importance
IMPORTANCE_TRAIN_SHARE = 0.8
IMPORTANCE_REPEATS = 15

# Download
TICKER = "^BVSP"
FX_TICKER = "BRL=X"
DATA_START = "2010-01-01"

HAR_FEATURES = ["f_logrv_1", "f_logrv_5", "f_logrv_22"]
