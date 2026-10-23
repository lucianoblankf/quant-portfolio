"""Master runner for project 3. Run it from your IDE with the project folder as the working
directory. It runs the tests first, then the numbered scripts in order."""

import runpy
import sys

import pytest

if pytest.main(["-q"]) != 0:
    sys.exit("Tests failed, stopping.")

for script in ("01_get_data.py", "02_bootstrap.py", "03_risk.py", "04_figures.py"):
    runpy.run_path(script, run_name="__main__")
