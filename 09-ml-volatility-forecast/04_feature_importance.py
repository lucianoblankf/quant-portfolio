"""04: permutation importance of the boosting model (fit on the first 80%, shuffle on the last 20%)."""

import pandas as pd
from sklearn.inspection import permutation_importance

from src import config, models, reporting

reporting.section("04 Feature importance")

dataset = pd.read_parquet("data/processed/dataset.parquet")
features = [c for c in dataset if c.startswith("f_")]

cut = int(len(dataset) * config.IMPORTANCE_TRAIN_SHARE)
train = dataset.iloc[: cut - config.HORIZON].dropna(subset=["y"])
test = dataset.iloc[cut:].dropna(subset=["y"])

model = models.boosting_model().fit(train[features], train["y"])
result = permutation_importance(
    model,
    test[features],
    test["y"],
    n_repeats=config.IMPORTANCE_REPEATS,
    random_state=config.SEED,
    scoring="neg_mean_squared_error",
)
importance = (
    pd.DataFrame({"feature": features, "mse_increase": result.importances_mean})
    .sort_values("mse_increase", ascending=False)
    .reset_index(drop=True)
)
reporting.save_table(importance, "feature_importance")
reporting.show_table(importance, "Permutation importance (increase in MSE when the feature is shuffled)")
