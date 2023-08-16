from typing import Any, Callable

import click


def opt_args(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-a", "--arg", multiple=True, help="Argument value to use.", type=(str, str)
    )  # type: ignore[var-annotated]
    _opt(fn)
    return fn
