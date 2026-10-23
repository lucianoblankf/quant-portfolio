"""Console reporting and table export helpers (rich for the console, files in tabs/)."""

from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


def section(title: str) -> None:
    """Print a section rule, one per script."""
    console.rule(f"[bold]{title}")


def info(message: str) -> None:
    console.print(f"[blue]i[/] {message}")


def success(message: str) -> None:
    console.print(f"[green]ok[/] {message}")


def warn(message: str) -> None:
    console.print(f"[yellow]![/] {message}")


def show_table(tbl: pd.DataFrame, title: str | None = None, digits: int = 4) -> None:
    """Print a dataframe as a rich table (index included when it is named)."""
    out = Table(title=title, show_lines=False)
    frame = tbl.reset_index() if tbl.index.name or isinstance(tbl.index, pd.MultiIndex) else tbl
    for col in frame.columns:
        out.add_column(str(col), justify="right" if pd.api.types.is_numeric_dtype(frame[col]) else "left")
    for _, row in frame.iterrows():
        out.add_row(*[f"{v:,.{digits}f}" if isinstance(v, float) else str(v) for v in row])
    console.print(out)


def save_table(tbl: pd.DataFrame, name: str, directory: str = "tabs", digits: int = 4) -> None:
    """Save a table as .csv, .tex and .html."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    rounded = tbl.apply(lambda col: col.round(digits) if pd.api.types.is_float_dtype(col) else col)
    tbl.to_csv(folder / f"{name}.csv", index=False)
    rounded.to_latex(folder / f"{name}.tex", index=False, float_format=f"%.{digits}f")
    rounded.to_html(folder / f"{name}.html", index=False)
