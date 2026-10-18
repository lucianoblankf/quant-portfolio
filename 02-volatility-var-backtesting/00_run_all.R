# Master runner for project 2. Open this folder as the working directory in your IDE and run.

source("99_tests.R")       # checks with known answers
source("01_get_data.R")
source("02_clustering_and_garch.R")
source("03_rolling_var.R")  # slow part: rolling re-estimation (cached in data/processed)
source("04_backtest.R")
source("05_figures.R")
