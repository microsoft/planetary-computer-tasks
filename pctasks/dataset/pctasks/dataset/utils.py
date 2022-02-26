from typing import Any, Callable

import click

# Common click options


def opt_ds_config(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-d",
        "--dataset",
        type=click.Path(exists=True),
        help=(
            "Dataset configuration file to use. "
            "If None specified, will look for a 'dataset.yaml' "
            "in the current directory"
        ),
    )
    _opt(fn)
    return fn


def opt_collection(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "--collection",
        help=(
            "Collection ID to process. "
            "Must be supplied if multiple collections exist in the configuration."
        ),
    )
    _opt(fn)
    return fn


def opt_dry_run(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-n", "--dry-run", is_flag=True, help="Don't submit, just print the workflow."
    )
    _opt(fn)
    return fn
