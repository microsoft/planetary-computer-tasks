import logging

import click

from pctasks.client.client import PCTasksClient
from pctasks.client.settings import ClientSettings
from pctasks.client.submit.template import template_workflow_file
from pctasks.core.cli import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowSubmitMessage

logger = logging.getLogger(__name__)


@click.command("workflow")
@click.argument("workflow_path")
@click.pass_context
def file_cmd(ctx: click.Context, workflow_path: str) -> None:
    """Submit the workflow at FILE

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    context: PCTasksCommandContext = ctx.obj
    settings = ClientSettings.get(context.profile, context.settings_file)

    workflow = template_workflow_file(workflow_path)

    msg = WorkflowSubmitMessage(workflow=workflow)
    submit_client = PCTasksClient(settings)
    submit_client.submit_workflow(msg)

    with open("test_workflow_argo.json", "w") as f:
        f.write(msg.json(indent=2))

    with open("test_workflow_argo.yaml", "w") as f:
        f.write(msg.to_yaml())

    click.echo(click.style(f"Submitted workflow with run ID: {msg.run_id}", fg="green"))


@click.group("submit")
@click.pass_context
def submit_cmd(ctx: click.Context) -> None:
    """Submit tasks to a PCTasks task queue."""
    pass


submit_cmd.add_command(file_cmd)
