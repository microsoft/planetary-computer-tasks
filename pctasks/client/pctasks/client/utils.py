import logging
from typing import Any, Dict, Optional

import click
import requests

from pctasks.cli.cli import cli_output, cli_print
from pctasks.client.client import PCTasksClient
from pctasks.client.errors import ConfirmationError, NoWorkflowIDError
from pctasks.client.settings import ClientSettings
from pctasks.core.models.workflow import (
    WorkflowArgumentError,
    WorkflowDefinition,
    WorkflowSubmitRequest,
)

logger = logging.getLogger(__name__)


def status_emoji(status: str) -> str:
    if status.lower() == "completed":
        return "✅"
    if status.lower() == "failed":
        return "❌"
    if status.lower() == "running":
        return "🏃"
    if status.lower() == "cancelled":
        return "🚫"
    else:
        return "🕖"


def cli_submit_workflow(
    ctx: click.Context,
    workflow_id: str,
    args: Optional[Dict[str, Any]],
    client: Optional[PCTasksClient] = None,
) -> None:
    """Submit a workflow to the PCTasks task queue."""
    if not client:
        client = PCTasksClient(settings=ClientSettings.from_context(ctx.obj))

    try:
        submit_result = client.submit_workflow(
            workflow_id, WorkflowSubmitRequest(args=args) if args else None
        )
    except ConfirmationError:
        cli_print("[red]Submit cancelled by user[/red]")
        raise click.Abort()
    except WorkflowArgumentError as e:
        cli_print("[red]Argument errors:[/red]")
        for error in e.errors:
            cli_print(f"  [red bold]{error}[/red bold]")
        ctx.exit(1)
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        cli_print("[red]Error submitting workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        ctx.exit(1)

    cli_print(
        "[green]Submitted workflow with run ID: [/green]",
    )
    cli_output(submit_result.run_id)
    ctx.exit(0)


def cli_handle_workflow(
    ctx: click.Context,
    workflow_def: WorkflowDefinition,
    args: Optional[Dict[str, Any]],
    workflow_id: Optional[str] = None,
    upsert: bool = False,
    upsert_and_submit: bool = False,
    client: Optional[PCTasksClient] = None,
) -> None:
    """Handle a workflow definition created through the CLI.

    If `upsert` is True, the workflow will be upserted to the server.
    If `upsert_and_submit` is True, the workflow will also be submitted.

    The sys.stdout output will be the workflow definition content if neither
    upsert or submit_and_upsert is supplied, the workflow ID if upsert is supplied,
    or the run ID if upsert_and_submit is supplied.
    """
    if not workflow_id:
        if not workflow_def.workflow_id:
            raise NoWorkflowIDError(
                "If no workflow ID is specified, "
                "the workflow definition must have a "
                "workflow_id field set"
            )
        workflow_id = workflow_def.workflow_id

    if not client:
        client = PCTasksClient(settings=ClientSettings.from_context(ctx.obj))

    if upsert or upsert_and_submit:
        cli_print(click.style(f"  Saving {workflow_id}...", fg="green"))
        client.upsert_workflow(workflow_def)
        if upsert_and_submit:
            cli_print(click.style(f"  Submitting {workflow_id}...", fg="green"))
            cli_submit_workflow(ctx, workflow_id, args, client=client)
        else:
            cli_output(workflow_id)
    else:
        cli_output(workflow_def.to_yaml())
