"""Master runner for project 9. Run it from your IDE with the project folder as the working
directory. It runs the tests first, then the numbered scripts in order."""

import runpy
import sys

import pytest

if pytest.main(["-q"]) != 0:
    sys.exit("Tests failed, stopping.")

for script in (
    "01_get_data.py",
    "02_walk_forward.py",
    "03_evaluation.py",
    "04_feature_importance.py",
    "05_figures.py",
):
    runpy.run_path(script, run_name="__main__")
