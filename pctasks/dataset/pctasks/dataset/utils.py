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
        "-c",
        "--collection",
        help=(
            "Collection ID to process. "
            "Must be supplied if multiple collections exist in the configuration."
        ),
    )
    _opt(fn)
    return fn


def opt_upsert(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option("-u", "--upsert", is_flag=True, help="Upsert the workflow.")
    _opt(fn)
    return fn


def opt_submit(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option("-s", "--submit", is_flag=True, help="Submit the workflow.")
    _opt(fn)
    return fn


def opt_workflow_id(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "--workflow-id",
        help=("Workflow ID to use instead of default."),
    )
    _opt(fn)
    return fn
