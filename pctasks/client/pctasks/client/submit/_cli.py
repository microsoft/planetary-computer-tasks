import logging
import sys
from typing import List, Optional, Tuple

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


def cli_submit_workflow(
    submit_client: PCTasksClient,
    msg: WorkflowSubmitMessage,
    settings: Optional[ClientSettings] = None,
) -> None:
    """Submit a workflow to the PCTasks task queue."""
    settings = settings or ClientSettings.get()
    try:
        submit_client.submit_workflow(
            msg, confirmation_required=settings.confirmation_required
        )
    except ConfirmationError:
        rprint("[red]Submit cancelled by user[/red]")
        raise click.Abort()

    rprint(
        "[green]Submitted workflow with run ID: [/green]",
        file=sys.stderr,
    )
    cli_output(msg.run_id)


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
    cli_submit_workflow(submit_client, msg, settings)
