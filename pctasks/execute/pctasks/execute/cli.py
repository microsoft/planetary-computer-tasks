from typing import Any, Dict, List, Optional

import click

from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.storage import StorageFactory, get_storage_for_file
from pctasks.execute.local import LocalRunner
from pctasks.task.context import TaskContext


@click.command("workflow")
@click.argument("workflow")
@click.option(
    "-a",
    "--arg",
    multiple=True,
    help="Arguments to pass to the workflow. Formatted as 'key=value'",
)
@click.option("-o", "--output", help="URI of folder to write the task result to")
def workflow_cmd(workflow: str, args: List[str], output: Optional[str] = None) -> None:
    workflow_args: Optional[Dict[str, Any]] = None
    if args:
        workflow_args = {}
        for arg in args:
            split_args = arg.split("=")
            if not len(split_args) == 2:
                raise click.UsageError(f"Invalid argument: {arg}")
            workflow_args[split_args[0]] = split_args[1]

    storage, path = get_storage_for_file(workflow)
    workflow_yaml = storage.read_text(path)
    workflow_config = WorkflowConfig.from_yaml(workflow_yaml)

    runner = LocalRunner()
    runner.run_workflow(
        workflow_config,
        TaskContext(storage_factory=StorageFactory()),
        args=workflow_args,
        output_uri=output,
    )


@click.group("execute")
@click.pass_context
def execute_cmd(ctx: click.Context) -> None:
    """PCTasks commands for executing workflows locally."""
    pass


execute_cmd.add_command(workflow_cmd)
