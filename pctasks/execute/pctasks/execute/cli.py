from typing import Any, Dict, List, Optional

import click

from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.storage import StorageFactory, get_storage_for_file
from pctasks.execute.runner.local import LocalRunner
from pctasks.task.context import TaskContext


@click.command("local")
@click.argument("workflow")
@click.option(
    "-a",
    "--arg",
    multiple=True,
    help="Arguments to pass to the workflow. Formatted as 'key=value'",
)
@click.option("-o", "--output", help="URI of folder to write the task result to")
def local_cmd(workflow: str, args: List[str], output: Optional[str] = None) -> None:
    """Execute a workflow using a local runner.

    This executes a workflow sequentially and runs tasks
    in the local environment. Useful for testing.
    """
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


@click.command("batch")
@click.argument("workflow")
@click.option(
    "-a",
    "--arg",
    multiple=True,
    help="Arguments to pass to the workflow. Formatted as 'key=value'",
)
@click.option("-o", "--output", help="URI of folder to write the task result to")
def batch_cmd(workflow: str, args: List[str], output: Optional[str] = None) -> None:
    """Execute a workflow using a local runner.

    This executes a workflow sequentially and runs tasks
    in the local environment. Useful for testing.
    """
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


@click.group("run")
@click.pass_context
def run_cmd(ctx: click.Context) -> None:
    """PCTasks commands for running workflows."""
    pass


run_cmd.add_command(local_cmd)
run_cmd.add_command(batch_cmd)