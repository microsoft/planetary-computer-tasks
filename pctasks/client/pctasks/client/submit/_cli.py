import logging
import sys
from typing import List, Tuple

import click
from rich import print as rprint

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.errors import ConfirmationError
from pctasks.client.settings import ClientSettings
from pctasks.client.submit.template import template_workflow_file
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowSubmitMessage

logger = logging.getLogger(__name__)


def workflow_cmd(
    ctx: click.Context, workflow_path: str, arg: List[Tuple[str, str]]
) -> None:
    """Submit the workflow at FILE

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow = template_workflow_file(workflow_path)

    msg = WorkflowSubmitMessage(workflow=workflow, args=dict(arg))
    submit_client = PCTasksClient(settings)
    try:
        submit_client.submit_workflow(msg)
    except ConfirmationError:
        rprint("[red]Submit cancelled by user[/red]")
        raise click.Abort()

    rprint(
        f"[green]Submitted workflow with run ID: [/green][bold{msg.run_id}[/bold]",
        file=sys.stderr,
    )
    cli_output(msg.run_id)
