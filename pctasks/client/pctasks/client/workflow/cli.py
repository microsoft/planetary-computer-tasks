import logging
from typing import IO, List, Optional, Tuple

import click

from pctasks.client.workflow.options import opt_args

logger = logging.getLogger(__name__)


@click.group("workflow")  # type: ignore[arg-type]
@click.option(
    "-p",
    "--pretty-print",
    is_flag=True,
    help="Pretty print output, e.g. syntax highlight YAML",
)
@click.pass_context
def workflow_cmd(ctx: click.Context, pretty_print: bool) -> None:
    """Create, update, and submit workflows"""
    from pctasks.client.context import ClientCommandContext
    from pctasks.core.context import PCTasksCommandContext

    pctasks_context: PCTasksCommandContext = ctx.obj
    ctx.obj = ClientCommandContext(
        profile=pctasks_context.profile,
        settings_file=pctasks_context.settings_file,
        pretty_print=pretty_print,
    )


@workflow_cmd.command("submit")
@click.argument("workflow_id")
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
    from . import commands

    ctx.exit(commands.submit_workflow(ctx, workflow_id, args={a[0]: a[1] for a in arg}))


@workflow_cmd.command("upsert-and-submit")
@click.argument("workflow", type=click.File("r"))
@click.option("-w", "--workflow-id", help="Workflow ID, if not specified in workflow")
@opt_args
@click.pass_context
def upsert_and_submit_cmd(
    ctx: click.Context,
    workflow: IO[str],
    workflow_id: Optional[str],
    arg: List[Tuple[str, str]],
) -> None:
    """Submit the workflow from local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import commands

    ctx.exit(
        commands.upsert_and_submit_workflow(
            ctx, workflow, workflow_id, args={a[0]: a[1] for a in arg}
        )
    )


@workflow_cmd.command("create")
@click.argument("workflow", type=click.File("r"))
@click.option("-w", "--workflow-id", help="Workflow ID, if not specified in workflow")
@opt_args
@click.pass_context
def create_cmd(
    ctx: click.Context,
    workflow: IO[str],
    workflow_id: Optional[str],
    arg: List[Tuple[str, str]],
) -> None:
    """Create a workflow from a definition at local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import commands

    ctx.exit(
        commands.create_workflow(
            ctx, workflow, workflow_id=workflow_id, args={a[0]: a[1] for a in arg}
        )
    )


@workflow_cmd.command("update")
@click.argument("workflow", type=click.File("r"))
@click.option("-w", "--workflow-id", help="Workflow ID, if not specified in workflow")
@opt_args
@click.pass_context
def update_cmd(
    ctx: click.Context,
    workflow: IO[str],
    workflow_id: Optional[str],
    arg: List[Tuple[str, str]],
) -> None:
    """Update a workflow from a definition at local file or stdin

    Use "-" to read the workflow from stdin.
    """
    from . import commands

    ctx.exit(
        commands.update_workflow(
            ctx, workflow, workflow_id=workflow_id, args={a[0]: a[1] for a in arg}
        )
    )


@workflow_cmd.command("get")  # type: ignore[arg-type]
@click.argument("workflow_id")
@click.pass_context
def get_cmd(
    ctx: click.Context,
    workflow_id: str,
) -> None:
    """Get the workflow with the given ID"""
    from . import commands

    ctx.exit(commands.get_workflow(ctx, workflow_id=workflow_id))


@workflow_cmd.command("list")  # type: ignore[arg-type]
@click.option("-s", "--sort-by", help="Property to sort by")
@click.option("-d", "--desc", help="Sort descending", is_flag=True)
@click.pass_context
def list_cmd(ctx: click.Context, sort_by: Optional[str], desc: bool) -> None:
    """List all workflows"""
    from . import commands

    ctx.exit(commands.list_workflows(ctx, sort_by=sort_by, desc=desc))
