import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from pctasks.cli.cli import setup_logging
from pctasks.core.models.workflow import WorkflowConfig, WorkflowSubmitMessage
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import assert_workflow_is_successful
from pctasks.execute.runner.remote import RemoteRunner, WorkflowFailedError
from pctasks.execute.settings import ExecuteSettings


def run_workflow(
    workflow: WorkflowConfig, run_id: str, args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    workflow_failed = False
    try:
        submit_message = WorkflowSubmitMessage(
            workflow=workflow, run_id=run_id, args=args
        )

        settings = ExecuteSettings.get()
        settings = settings.copy(deep=True)
        settings.task_poll_seconds = 5
        runner = RemoteRunner(settings)

        result = runner.run_workflow(submit_message)

    except WorkflowFailedError:
        workflow_failed = True

    assert_workflow_is_successful(run_id=run_id, timeout_seconds=20)

    # If the records show the workflow as success, ensure it didn't
    # fail from runner.
    assert not workflow_failed

    return result


def test_remote_processes_job_with_two_tasks():
    setup_logging(logging.INFO)
    workflow_yaml = """
args:
- base_output_dir

name: Test workflow for remote runner 1
dataset:
  owner: microsoft
  name: test-remote-1
jobs:
  job-1:
    tasks:
    - id: task-1
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        output_dir: "${{ args.base_output_dir }}/job-1-task-1"
      schema_version: 1.0.0
    - id: task-2
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        uri: ${{ tasks.task-1.output.uri }}
        output_dir: "${{ args.base_output_dir }}/job-1-task-2"
      schema_version: 1.0.0
    needs: create-chunks
schema_version: 1.0.0
"""
    with temp_azurite_blob_storage() as storage:
        output_dir = storage.get_uri()
        run_id = uuid4().hex

        run_workflow(
            WorkflowConfig.from_yaml(workflow_yaml),
            run_id=run_id,
            args={"base_output_dir": output_dir},
        )

        last_task_output_paths = list(
            storage.list_files(name_starts_with="job-1-task-2/")
        )

        assert len(last_task_output_paths) == 1


def test_remote_processes_dataset_like_workflow():
    setup_logging(logging.INFO)
    workflow_yaml = """
args:
- base_output_dir

name: Test workflow for remote runner 1
dataset:
  owner: microsoft
  name: test-remote-1
jobs:
  job-1:
    tasks:
    - id: task-1
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        output_dir: "${{ args.base_output_dir }}/job-1-task-1"
        options:
          num_outputs: 2
      schema_version: 1.0.0
  job-2:
    tasks:
    - id: task-1
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        uri: ${{ item.uri }}
        output_dir: "${{ args.base_output_dir }}/job-2-task-1"
        options:
          num_outputs: 2
      schema_version: 1.0.0
    foreach:
      items: ${{ jobs.job-1.tasks.task-1.output.uris }}
    needs: job-1
  job-3:
    tasks:
    - id: task-1
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        uri: ${{ item.uri }}
        output_dir: "${{ args.base_output_dir }}/job-3-task-1"
      schema_version: 1.0.0
    - id: task-2
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        uri: ${{ tasks.task-1.output.uri }}
        output_dir: "${{ args.base_output_dir }}/job-3-task-2"
      schema_version: 1.0.0
    foreach:
      items: ${{ jobs.job-2.tasks.task-1.output.uris }}
    needs: create-chunks
schema_version: 1.0.0
"""
    with temp_azurite_blob_storage() as storage:
        output_dir = storage.get_uri()
        run_id = uuid4().hex

        run_workflow(
            WorkflowConfig.from_yaml(workflow_yaml),
            run_id=run_id,
            args={"base_output_dir": output_dir},
        )

        last_task_output_paths = list(
            storage.list_files(name_starts_with="job-3-task-2/")
        )

        assert len(last_task_output_paths) == 4
