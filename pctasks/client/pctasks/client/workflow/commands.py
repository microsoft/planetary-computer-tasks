import logging
from pathlib import Path
from typing import IO, Any, Dict, Optional, Tuple

import click
import requests
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from pctasks.cli.cli import cli_output, cli_print
from pctasks.client.client import PCTasksClient
from pctasks.client.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.context import ClientCommandContext
from pctasks.client.errors import ConfirmationError, NoWorkflowIDError
from pctasks.client.settings import ClientSettings
from pctasks.client.workflow.template import template_workflow_contents
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import (
    WorkflowArgumentError,
    WorkflowDefinition,
    WorkflowSubmitRequest,
)

logger = logging.getLogger(__name__)


def _get_workflow_def(
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> Tuple[WorkflowDefinition, str]:
    workflow_base_dir: Optional[Path] = None
    if hasattr(workflow_io, "name"):
        workflow_base_dir = Path(workflow_io.name).parent

    workflow_contents = workflow_io.read()
    workflow_def = template_workflow_contents(
        workflow_contents, base_path=workflow_base_dir
    )

    if args:
        workflow_def = workflow_def.template_args(args)

    workflow_id = workflow_id or workflow_def.workflow_id
    if not workflow_id:
        raise click.UsageError(
            "Workflow ID must be specified in the definition or "
            "supplied as an argument."
        )
    return workflow_def, workflow_id


def create_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> int:
    """Create the workflow from the definition at workflow_io"""
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)

    client = PCTasksClient(settings)

    try:
        client.create_workflow(workflow_def, workflow_id)
        return 0
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        cli_print("[red]Error creating workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        return 1


def update_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> int:
    """Create the workflow from the definition at workflow_io"""
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)

    client = PCTasksClient(settings)

    try:
        client.update_workflow(workflow_def, workflow_id)
        return 0
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        cli_print("[red]Error updating workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        return 1


def upsert_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> int:
    """Create or update the workflow from the definition at workflow_io"""
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)

    try:
        client.upsert_workflow(workflow_def, workflow_id)
        return 0
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        cli_print("[red]Error upserting workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        return 1


def list_workflows(
    ctx: click.Context, sort_by: Optional[str] = None, desc: bool = False
) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)

    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        records = client.list_workflows(sort_by=sort_by, descending=desc)
        if records is None:
            console.print("[bold red]No records found.")
            return NOT_FOUND_EXIT_CODE
        table = Table()
        table.add_column("id")
        table.add_column("name")

        for record in records:
            table.add_row(record.get_id(), record.workflow.definition.name)

    console.print(table)
    return 0


def get_workflow(ctx: click.Context, workflow_id: str) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    records_context: ClientCommandContext = ctx.obj
    console = Console(stderr=True)

    record = client.get_workflow(workflow_id)
    if not record:
        console.print("[bold red]No record found.")
        return NOT_FOUND_EXIT_CODE

    if records_context.pretty_print:
        console.print(Syntax(record.to_yaml(), "yaml"))
    else:
        cli_output(record.to_yaml())
    return 0


def submit_workflow(
    ctx: click.Context,
    workflow_id: str,
    args: Optional[Dict[str, Any]],
    client: Optional[PCTasksClient] = None,
    auto_confirm: bool = False,
) -> int:
    """Submit a workflow to the PCTasks task queue."""
    if not client:
        client = PCTasksClient(settings=ClientSettings.from_context(ctx.obj))

    try:
        submit_result = client.submit_workflow(
            workflow_id,
            WorkflowSubmitRequest(args=args) if args else None,
            auto_confirm=auto_confirm,
        )
    except ConfirmationError:
        cli_print("[red]Submit cancelled by user[/red]")
        raise click.Abort()
    except WorkflowArgumentError as e:
        cli_print("[red]Argument errors:[/red]")
        for error in e.errors:
            cli_print(f"  [red bold]{error}[/red bold]")
        return 1
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        cli_print("[red]Error submitting workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        return 1

    cli_print(
        "[green]Submitted workflow with run ID: [/green]",
    )
    cli_output(submit_result.run_id)
    return 0


def upsert_and_submit_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> int:
    """Create or update the workflow from the definition at workflow_io"""
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)
    try:
        client.upsert_workflow(workflow_def, workflow_id)
    except requests.HTTPError as e:
        cli_print("[red]Error upserting workflow![/red]")
        cli_print(f"[red bold]{e}[/red bold]")
        return 1

    return submit_workflow(ctx, workflow_id, args, client)


def cli_handle_workflow(
    ctx: click.Context,
    workflow_def: WorkflowDefinition,
    args: Optional[Dict[str, Any]],
    workflow_id: Optional[str] = None,
    upsert: bool = False,
    upsert_and_submit: bool = False,
    client: Optional[PCTasksClient] = None,
    auto_confirm: bool = False,
) -> int:
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

    if workflow_id:
        workflow_def = workflow_def.copy(update={"workflow_id": workflow_id})

    if upsert or upsert_and_submit:
        cli_print(f"[green]  Saving {workflow_id}...[/green]")
        client.upsert_workflow(workflow_def, auto_confirm=auto_confirm)
        if upsert_and_submit:
            cli_print(f"[green]  Submitting {workflow_id}...[/green]")
            return submit_workflow(
                ctx, workflow_id, args, client=client, auto_confirm=auto_confirm
            )
        else:
            cli_output(workflow_id)
            return 0
    else:
        cli_output(workflow_def.to_yaml())
        return 0
