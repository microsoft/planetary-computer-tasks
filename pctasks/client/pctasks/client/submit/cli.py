import logging
from typing import List, Tuple

import click

from pctasks.client.submit.options import opt_args

logger = logging.getLogger(__name__)


@click.command("workflow")
@click.argument("workflow_path")
@opt_args
@click.pass_context
def file_cmd(
    ctx: click.Context, workflow_path: str, arg: List[Tuple[str, str]]
) -> None:
    """Submit the workflow at FILE

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    from . import _cli

    return _cli.file_cmd(ctx, workflow_path, arg)


@click.group("submit")
@click.pass_context
def submit_cmd(ctx: click.Context) -> None:
    """Submit tasks to a PCTasks task queue."""
    pass


submit_cmd.add_command(file_cmd)
