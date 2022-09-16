import logging
import sys
from pathlib import Path
from typing import IO, Dict, List, Optional, Tuple

import click
import requests
from rich import print as rprint

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.errors import ConfirmationError
from pctasks.client.settings import ClientSettings
from pctasks.client.submit.template import template_workflow_contents
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowConfig, WorkflowSubmitMessage

logger = logging.getLogger(__name__)


def cli_submit_workflow(
    workflow: WorkflowConfig,
    args: Optional[Dict[str, str]],
    settings: Optional[ClientSettings] = None,
) -> int:
    """Submit a workflow to the PCTasks task queue."""
    settings = settings or ClientSettings.get()
    submit_client = PCTasksClient(settings)

    msg = WorkflowSubmitMessage(workflow=workflow, args=args)
    settings.add_default_arguments(msg)

    args_errors = msg.workflow.get_argument_errors(msg.args)
    if args_errors:
        rprint("[red]Argument errors:[/red]")
        for error in args_errors:
            rprint(f"  [red bold]{error}[/red bold]")
        return 1

    try:
        submit_client.submit_workflow(
            msg, confirmation_required=settings.confirmation_required
        )
    except ConfirmationError:
        rprint("[red]Submit cancelled by user[/red]")
        raise click.Abort()
    except requests.HTTPError as e:
        logger.debug(e, exc_info=True)
        rprint("[red]Error submitting workflow![/red]", file=sys.stderr)
        rprint(f"[red bold]{e}[/red bold]", file=sys.stderr)
        sys.exit(1)

    rprint(
        "[green]Submitted workflow with run ID: [/green]",
        file=sys.stderr,
    )
    cli_output(msg.run_id)
    return 0


def workflow_cmd(
    ctx: click.Context, workflow_io: IO[str], arg: List[Tuple[str, str]]
) -> None:
    """Submit the workflow at FILE

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow_base_dir: Optional[Path] = None
    if hasattr(workflow_io, "name"):
        workflow_base_dir = Path(workflow_io.name).parent

    workflow_contents = workflow_io.read()
    workflow = template_workflow_contents(
        workflow_contents, base_path=workflow_base_dir
    )

    ctx.exit(cli_submit_workflow(workflow, dict(arg), settings))
