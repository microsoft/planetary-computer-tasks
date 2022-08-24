import logging
from typing import IO, List, Tuple

import click

from pctasks.client.submit.options import opt_args

logger = logging.getLogger(__name__)


@click.command("workflow")
@click.argument("workflow", type=click.File("r"))
@opt_args
@click.pass_context
def workflow_cmd(
    ctx: click.Context, workflow: IO[str], arg: List[Tuple[str, str]]
) -> None:
    """Submit the workflow from local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import _cli

    return _cli.workflow_cmd(ctx, workflow, arg)


@click.group("submit")
@click.pass_context
def submit_cmd(ctx: click.Context) -> None:
    """Submit tasks to a PCTasks task queue."""
    pass


submit_cmd.add_command(workflow_cmd)
