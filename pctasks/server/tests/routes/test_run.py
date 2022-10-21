from starlette.testclient import TestClient

from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.utils import ignore_ssl_warnings


def test_run_workflow_rejects_no_creds(client: TestClient) -> None:

    workflow = WorkflowSubmitMessage.from_yaml(
        """
workflow:
  id: test-workflow-noauth
  definition:
    name: Test workflow - run unit test
    dataset: test-remote-noauth
    jobs:
      job-1:
        id: job-1
        tasks:
        - id: task-1
          image: mock:latest
          task: pctasks.dev.task:test_task
          args:
            output_dir: blob://devstoreaccount1/taskio/scratch/arg-test/job-1-task-1
            options:
              num_outputs: 2
          schema_version: 1.0.0
    schema_version: 1.0.0
run_id: test-workflow-noauth
"""
    )

    with ignore_ssl_warnings():
        response = client.post(
            "/workflows/test-workflow-noauth/submit", json=workflow.dict()
        )
        assert response.status_code == 401
