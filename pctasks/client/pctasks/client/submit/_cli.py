import logging
from typing import List, Tuple

import click

from pctasks.client.client import PCTasksClient
from pctasks.client.settings import ClientSettings
from pctasks.client.submit.template import template_workflow_file
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowSubmitMessage

logger = logging.getLogger(__name__)


def file_cmd(
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
    submit_client.submit_workflow(msg)

    with open("test_workflow_argo.json", "w") as f:
        f.write(msg.json(indent=2))

    with open("test_workflow_argo.yaml", "w") as f:
        f.write(msg.to_yaml())

    click.echo(click.style(f"Submitted workflow with run ID: {msg.run_id}", fg="green"))
