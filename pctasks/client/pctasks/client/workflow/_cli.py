import logging
import sys
from pathlib import Path
from typing import IO, Any, Dict, Optional, Tuple

import click
import requests
from rich import print as rprint

from pctasks.client.client import PCTasksClient
from pctasks.client.settings import ClientSettings
from pctasks.client.workflow.template import template_workflow_contents
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowDefinition

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
            "Workflow ID must be specified in the definition or with --id"
        )
    return workflow_def, workflow_id


def cli_create_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> None:
    """Create the workflow from the definition at workflow_io"""
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)

    client = PCTasksClient(settings)

    try:
        client.create_workflow(workflow_def, workflow_id)
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        rprint("[red]Error submitting workflow![/red]", file=sys.stderr)
        rprint(f"[red bold]{e}[/red bold]", file=sys.stderr)
        ctx.exit(1)


def cli_update_workflow(
    ctx: click.Context,
    workflow_io: IO[str],
    workflow_id: Optional[str],
    args: Optional[Dict[str, Any]],
) -> None:
    """Create the workflow from the definition at workflow_io"""
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow_def, workflow_id = _get_workflow_def(workflow_io, workflow_id, args)

    client = PCTasksClient(settings)

    try:
        client.update_workflow(workflow_def, workflow_id)
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        rprint("[red]Error submitting workflow![/red]", file=sys.stderr)
        rprint(f"[red bold]{e}[/red bold]", file=sys.stderr)
        ctx.exit(1)
