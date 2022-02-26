"""Based on rich_dataframe, Apache 2.0 Licensed

https://github.com/khuyentran1401/rich-dataframe
"""
from datetime import datetime
from typing import Any

import pandas as pd
from rich import box
from rich.box import MINIMAL, SIMPLE, SIMPLE_HEAD, SQUARE
from rich.columns import Columns
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table

COLORS = ["cyan", "magenta", "red", "green", "blue", "purple"]


class DataFrameRender:
    """
    Parameters
    ----------
    df : pd.DataFrame
        The data you want to prettify
    row_limit : int, optional
        Number of rows to show, by default 20
    col_limit : int, optional
        Number of columns to show, by default 10
    first_rows : bool, optional
        Whether to show first n rows or last n rows, by default True.
        If this is set to False, show last n rows.
    first_cols : bool, optional
        Whether to show first n columns or last n columns, by default True.
        If this is set to False, show last n rows.
    delay_time : int, optional
        How fast is the animation, by default 5. Increase this to
        have slower animation.
    clear_console: bool, optional
         Clear the console before printing the table, by default
         True. If this is set to False the previous console input/output is maintained
    """

    def __init__(
        self,
        console: Console,
        df: pd.DataFrame,
        all: bool = False,
        row_limit: int = 20,
        col_limit: int = 10,
        first_rows: bool = True,
        first_cols: bool = True,
        delay_time: int = 5,
        clear_console: bool = False,
    ) -> None:
        self.console = console
        self.df = df.rename(columns={"emoji": ""})
        self.table = Table(
            show_footer=False, show_lines=True, box=box.MINIMAL_HEAVY_HEAD
        )
        self.table_centered = Columns((self.table,), align="center", expand=True)
        self.num_colors = len(COLORS)
        self.delay_time = delay_time
        self.row_limit = row_limit
        self.first_rows = first_rows
        self.col_limit = col_limit
        self.first_cols = first_cols
        self.clear_console = clear_console

        if first_cols:
            self.columns = [x for x in self.df.columns[0:col_limit] if x != "emoji"]
        else:
            self.columns = list(self.df.columns[-col_limit:])

        if all:
            self.rows = self.df.values
        else:
            if first_rows:
                self.rows = self.df.values[:row_limit]
            else:
                self.rows = self.df.values[-row_limit:]

        if self.clear_console:
            self.console.clear()

        self.is_truncated = len(self.rows) < len(self.df)

    def _add_columns(self) -> None:
        for col in self.columns:
            self.table.add_column(str(col))

    def _add_rows(self) -> None:
        for row in self.rows:
            if self.first_cols:
                row = row[: self.col_limit]
            else:
                row = row[-self.col_limit :]

            def _tostring(item: Any) -> str:
                if isinstance(item, datetime):
                    return item.strftime("%Y-%m-%d %H:%M:%S")
                return str(item)

            row = [_tostring(item) for item in row]
            self.table.add_row(*list(row))

    def _move_text_to_right(self) -> None:
        for i in range(len(self.table.columns)):
            self.table.columns[i].justify = "center"

    def _add_random_color(self) -> None:
        for i in range(len(self.table.columns)):
            self.table.columns[i].header_style = COLORS[i % self.num_colors]

    def _add_style(self) -> None:
        for i in range(len(self.table.columns)):
            self.table.columns[i].style = "bold " + COLORS[i % self.num_colors]

    def _adjust_box(self) -> None:
        for b in [SIMPLE_HEAD, SIMPLE, MINIMAL, SQUARE]:
            self.table.box = b

    def _dim_row(self) -> None:
        self.table.row_styles = ["none", "dim"]

    def _adjust_border_color(self) -> None:
        self.table.border_style = "bright_yellow"

    def _change_width(self) -> None:
        original_width = Measurement.get(
            self.console, self.table
        ).maximum  # type: ignore
        width_ranges = [
            [original_width, self.console.width, 2],
            [self.console.width, original_width, -2],
            [original_width, 90, -2],
            [90, original_width + 1, 2],
        ]

        for width_range in width_ranges:
            for width in range(*width_range):
                self.table.width = width

            self.table.width = None

    def _add_caption(self) -> None:
        if self.first_rows:
            row_text = "first"
        else:
            row_text = "last"
        if self.first_cols:
            col_text = "first"
        else:
            col_text = "last"

        self.table.caption = (
            f"Only the [bold magenta not dim] {row_text} {self.row_limit} "
            "rows[/bold magenta not dim] and the "
            f"[bold green not dim]{col_text} {self.col_limit} "
            "columns[/bold green not dim] are shown here."
        )

    def render(self, page: bool = False, all: bool = False) -> None:
        self._add_columns()
        self._add_rows()
        self._move_text_to_right()
        self._add_random_color()
        self._add_style()
        self._adjust_border_color()

        if page:
            with self.console.pager():
                self.console.print(self.table)
        else:
            if self.is_truncated:
                self._add_caption()
            self.console.print(self.table)
