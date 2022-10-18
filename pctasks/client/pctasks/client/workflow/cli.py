import logging
from typing import IO, List, Optional, Tuple

import click

from pctasks.client.workflow.options import opt_args

logger = logging.getLogger(__name__)


@click.command("submit")
@click.option("-w", "--workflow-id", help="Workflow ID")
@opt_args
@click.pass_context
def submit_cmd(
    ctx: click.Context,
    workflow_id: str,
    arg: List[Tuple[str, str]],
) -> None:
    """Submit the workflow from local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from ..utils import cli_submit_workflow

    return cli_submit_workflow(
        ctx, workflow_id=workflow_id, args={a[0]: a[1] for a in arg}
    )


@click.command("create")
@click.argument("workflow", type=click.File("r"))
@click.option("-w", "--workflow-id", help="Workflow ID, if not specified in workflow")
@click.pass_context
def create_cmd(
    ctx: click.Context,
    workflow: IO[str],
    workflow_id: Optional[str],
) -> None:
    """Create a workflow from a definition at local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import _cli

    return _cli.cli_create_workflow(ctx, workflow, workflow_id=workflow_id)


@click.command("update")
@click.argument("workflow", type=click.File("r"))
@click.option("-w", "--workflow-id", help="Workflow ID, if not specified in workflow")
@click.pass_context
def update_cmd(
    ctx: click.Context, workflow: IO[str], workflow_id: Optional[str]
) -> None:
    """Update a workflow from a definition at local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import _cli

    return _cli.cli_update_workflow(ctx, workflow, workflow_id=workflow_id)


@click.group("workflow")
@click.pass_context
def workflow_cmd(ctx: click.Context) -> None:
    """Submit tasks to a PCTasks task queue."""
    pass


workflow_cmd.add_command(submit_cmd)
workflow_cmd.add_command(create_cmd)
workflow_cmd.add_command(update_cmd)
