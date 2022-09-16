from base64 import b64decode
from typing import Any, Dict, List, Optional
from uuid import uuid4

import click

from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowConfig, WorkflowSubmitMessage
from pctasks.core.storage import StorageFactory, get_storage_for_file
from pctasks.run.settings import RunSettings
from pctasks.run.workflow.executor.remote import RemoteWorkflowExecutor
from pctasks.run.workflow.executor.simple import SimpleWorkflowExecutor
from pctasks.task.context import TaskContext


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

    runner = SimpleWorkflowExecutor()
    runner.run_workflow(
        workflow_config,
        TaskContext(storage_factory=StorageFactory(), run_id=workflow_config.name),
        args=workflow_args,
        output_uri=output,
    )


def remote_cmd(
    ctx: click.Context,
    workflow: str,
    args: List[str],
    new_id: bool,
    settings: Optional[str],
    sas: Optional[str],
) -> None:
    """Execute a workflow using a remote runner."""

    storage, path = get_storage_for_file(workflow, sas_token=sas)
    workflow_yaml = storage.read_text(path)
    submit_message = WorkflowSubmitMessage.from_yaml(workflow_yaml)

    if settings:
        run_settings = RunSettings.from_yaml(
            b64decode(settings.encode("utf-8")).decode("utf-8")
        )
    else:
        context: PCTasksCommandContext = ctx.obj
        run_settings = RunSettings.get(context.profile, context.settings_file)

    # TODO: Do we need to pass in args at run time vs workflow submit msg?
    workflow_args: Optional[Dict[str, Any]] = None
    if args:
        workflow_args = {}
        for a in args:
            split_args = a.split("=")
            if not len(split_args) == 2:
                raise click.UsageError(f"Invalid argument: {a}")
            workflow_args[split_args[0]] = split_args[1]
        submit_message.args = {**(submit_message.args or {}), **workflow_args}

    runner = RemoteWorkflowExecutor(run_settings)

    if new_id:
        submit_message.run_id = uuid4().hex

    runner.execute_workflow(submit_message)
