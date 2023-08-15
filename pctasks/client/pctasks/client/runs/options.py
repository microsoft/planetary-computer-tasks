from typing import Any, Callable

import click


def opt_page(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-p", "--page", is_flag=True, help="Page output."
    )  # type: ignore[var-annotated]
    _opt(fn)
    return fn


def opt_all(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-a", "--all", is_flag=True, help="Print all output, even if large."
    )  # type: ignore[var-annotated]
    _opt(fn)
    return fn


def opt_status(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option("-s", "--status", help="Filter by status.")  # type: ignore[var-annotated]  # noqa: E501
    _opt(fn)
    return fn
