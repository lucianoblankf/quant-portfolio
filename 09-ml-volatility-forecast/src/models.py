"""Model definitions: the fitted models and the features each one uses."""

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src import config

MODEL_ORDER = [
    "Naive (yesterday)",
    "EWMA 0.94",
    "HAR (OLS)",
    "HAR + extras (Ridge)",
    "Random forest",
    "Gradient boosting",
]


def boosting_model() -> HistGradientBoostingRegressor:
    """The gradient-boosting model (also used for the permutation importance)."""
    return HistGradientBoostingRegressor(
        max_depth=3,
        learning_rate=0.05,
        max_iter=200,
        min_samples_leaf=50,
        l2_regularization=1.0,
        random_state=config.SEED,
    )


def fitted_models() -> dict:
    """The four models that are re-fitted in the walk-forward (naive and EWMA need no fit)."""
    return {
        "HAR (OLS)": LinearRegression(),
        "HAR + extras (Ridge)": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "Random forest": RandomForestRegressor(
            n_estimators=200, min_samples_leaf=30, max_features=0.5, n_jobs=-1, random_state=config.SEED
        ),
        "Gradient boosting": boosting_model(),
    }


def feature_sets(all_features: list) -> dict:
    """Columns used by each fitted model: HAR uses three, the others use every feature."""
    return {
        "HAR (OLS)": list(config.HAR_FEATURES),
        "HAR + extras (Ridge)": all_features,
        "Random forest": all_features,
        "Gradient boosting": all_features,
    }
