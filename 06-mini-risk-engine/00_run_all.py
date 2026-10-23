"""Master runner for project 6. Run it from your IDE with the project folder as the working
directory. It runs the tests first, then the numbered scripts in order."""

import runpy
import sys

import pytest

if pytest.main(["-q"]) != 0:
    sys.exit("Tests failed, stopping.")

for script in ("01_get_data.py", "02_var_es.py", "03_stress.py", "04_backtest.py", "05_figures.py"):
    runpy.run_path(script, run_name="__main__")
