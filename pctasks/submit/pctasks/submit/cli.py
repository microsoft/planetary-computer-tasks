import logging

import click

from pctasks.core.cli import PCTasksCommandContext, get_plugin_subcommands
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.submit.dataset import dataset_cmd
from pctasks.submit.template import template_workflow_file

logger = logging.getLogger(__name__)

PCTASKS_SUBMIT_ENTRY_POINT_GROUP = "pctasks.submit.commands"


@click.command("workflow")
@click.argument("workflow_path")
@click.pass_context
def file_cmd(ctx: click.Context, workflow_path: str) -> None:
    """Submit the workflow at FILE

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    from pctasks.submit.client import SubmitClient  # cli-perf
    from pctasks.submit.settings import SubmitSettings  # cli-perf

    context: PCTasksCommandContext = ctx.obj
    settings = SubmitSettings.get(context.profile, context.settings_file)

    workflow = template_workflow_file(workflow_path)

    msg = WorkflowSubmitMessage(workflow=workflow)
    with SubmitClient(settings) as submit_client:
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
submit_cmd.add_command(dataset_cmd)

for subcommand in get_plugin_subcommands(
    click.Command, PCTASKS_SUBMIT_ENTRY_POINT_GROUP
):
    submit_cmd.add_command(subcommand)
