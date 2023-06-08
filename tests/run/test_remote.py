import logging
from typing import Any, Dict, Optional
from uuid import uuid4

import pytest

from pctasks.cli.cli import setup_logging
from pctasks.core.cosmos.containers.workflow_runs import WorkflowRunsContainer
from pctasks.core.cosmos.containers.workflows import WorkflowsContainer
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.run import WorkflowRunRecord
from pctasks.core.models.workflow import (
    Workflow,
    WorkflowDefinition,
    WorkflowRecord,
    WorkflowSubmitMessage,
)
from pctasks.core.utils import ignore_ssl_warnings
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import assert_workflow_is_successful
from pctasks.run.settings import RunSettings, WorkflowExecutorConfig
from pctasks.run.workflow.executor.remote import (
    RemoteWorkflowExecutor,
    WorkflowFailedError,
)


def run_workflow(
    workflow_def: WorkflowDefinition, run_id: str, args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    workflow_failed = False
    workflow = Workflow.from_definition(workflow_def)
    try:
        submit_message = WorkflowSubmitMessage(
            workflow=workflow, run_id=run_id, args=args
        )

        run_settings = RunSettings.get()
        run_settings = run_settings.copy(deep=True)
        run_settings.task_poll_seconds = 5
        cosmosdb_settings = CosmosDBSettings.get()

        with RemoteWorkflowExecutor(
            WorkflowExecutorConfig(
                run_settings=run_settings, cosmosdb_settings=cosmosdb_settings
            )
        ) as runner:
            with ignore_ssl_warnings():
                # Make sure the workflow exists in the database
                with WorkflowsContainer(WorkflowRecord) as workflow_container:
                    workflow_container.put(
                        WorkflowRecord(workflow=workflow, workflow_id=workflow.id)
                    )

                # Mimic the server and write the workflow run record
                # before executing workflow
                with WorkflowRunsContainer(WorkflowRunRecord) as workflow_run_container:
                    workflow_run_container.put(
                        WorkflowRunRecord.from_submit_message(submit_message)
                    )

                result = runner.execute_workflow(submit_message)

    except WorkflowFailedError:
        workflow_failed = True

    assert_workflow_is_successful(run_id=run_id, timeout_seconds=20)

    # If the records show the workflow as success, ensure it didn't
    # fail from runner.
    assert not workflow_failed

    return result


@pytest.mark.usefixtures("cosmosdb_containers")
def test_remote_processes_job_with_two_tasks():
    setup_logging(logging.INFO)
    workflow_yaml = """
args:
- base_output_dir

id: test-remote-workflow-1
name: Test workflow for remote runner 1
dataset: test-remote-dataset-1
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
            WorkflowDefinition.from_yaml(workflow_yaml),
            run_id=run_id,
            args={"base_output_dir": output_dir},
        )

        last_task_output_paths = list(
            storage.list_files(name_starts_with="job-1-task-2/")
        )

        assert len(last_task_output_paths) == 1


@pytest.mark.usefixtures("cosmosdb_containers")
def test_remote_processes_dataset_like_workflow():
    setup_logging(logging.INFO)
    workflow_yaml = """
args:
- base_output_dir

id: test-remote-workflow-2
name: Test workflow for remote runner 1
dataset: test-remote-dataset-2
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
            WorkflowDefinition.from_yaml(workflow_yaml),
            run_id=run_id,
            args={"base_output_dir": output_dir},
        )

        last_task_output_paths = list(
            storage.list_files(name_starts_with="job-3-task-2/")
        )

        assert len(last_task_output_paths) == 4


@pytest.mark.usefixtures("cosmosdb_containers")
def test_remote_processes_job_with_pc_sas_token():
    setup_logging(logging.INFO)
    workflow_yaml = """
args:
- base_output_dir

tokens:
  ai4edataeuwest:
    containers:
      io-lulc:
        token: ${{ pc.get_token(ai4edataeuwest, io-lulc) }}

id: test-remote-workflow-1
name: Test workflow for remote runner 1
dataset: test-remote-dataset-1
jobs:
  job-1:
    tasks:
    - id: task-1
      image: mock:latest
      task: pctasks.dev.task:test_task
      args:
        check_exists_uri: blob://ai4edataeuwest/io-lulc/nine-class/01C_20170101-20180101.tif
        output_dir: "${{ args.base_output_dir }}/job-1-task-1"
      schema_version: 1.0.0
    needs: create-chunks
schema_version: 1.0.0
"""  # noqa: E501
    with temp_azurite_blob_storage() as storage:
        output_dir = storage.get_uri()
        run_id = uuid4().hex

        # Workflow will fail if the SAS token is invalid.
        run_workflow(
            WorkflowDefinition.from_yaml(workflow_yaml),
            run_id=run_id,
            args={"base_output_dir": output_dir},
        )
