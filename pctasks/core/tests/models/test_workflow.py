import pytest
from pydantic import ValidationError

from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)


def test_sets_job_id():
    workflow = WorkflowConfig.from_yaml(
        """
        name: A workflow*  *with* *asterisks
        dataset: microsoft/test-dataset

        jobs:
            test-job:
                tasks:
                - id: test-task
                  image_key: ingest-prod
                  task: tests.test_submit.MockTask
                  args:
                    hello: world
    """
    )
    assert workflow
    assert workflow.jobs["test-job"].id == "test-job"


def test_disallows_invalid_job_ids():
    with pytest.raises(ValidationError):
        WorkflowConfig(
            name="Test Workflow!",
            dataset="microsoft/test-dataset",
            jobs={
                "A job / task / thing": JobConfig(
                    tasks=[
                        TaskConfig(
                            id="submit_unit_test",
                            image="pctasks-ingest:latest",
                            task="tests.test_submit.MockTask",
                            args={"hello": "world"},
                        )
                    ],
                )
            },
        )


def test_args():
    workflow = """
    name: Test workflow
    dataset: microsoft/test-dataset

    args:
      - name

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow = WorkflowConfig.from_yaml(workflow)
    submit_message = WorkflowSubmitMessage(workflow=workflow, args={"name": "world"})
    templated = submit_message.get_workflow_with_templated_args()
    assert templated.jobs["test-job"].tasks[0].args["hello"] == "world"


def test_unexpected_args():
    workflow = """
    name: Test workflow
    dataset: microsoft/test-dataset

    args:
      - name

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow = WorkflowConfig.from_yaml(workflow)
    try:
        _ = WorkflowSubmitMessage(
            workflow=workflow, args={"nombre": "mundo", "name": "world"}
        )
    except ValidationError as e:
        assert "Unexpected args" in str(e)
        return


def test_missing_and_unexpected_args():
    workflow = """
    name: Test workflow
    dataset: microsoft/test-dataset

    args:
      - name

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow = WorkflowConfig.from_yaml(workflow)
    try:
        _ = WorkflowSubmitMessage(workflow=workflow, args={"nombre": "mundo"})
    except ValidationError as e:
        assert "Unexpected args" in str(e)
        assert "Args expected" in str(e)
        return


def test_missing_args():
    workflow = """
    name: Test workflow
    dataset: microsoft/test-dataset

    args:
      - name

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow = WorkflowConfig.from_yaml(workflow)
    try:
        _ = WorkflowSubmitMessage(workflow=workflow)
    except ValidationError as e:
        assert "Args expected" in str(e)
        return


def test_job_ids_no_commas():
    with pytest.raises(ValidationError):
        _ = WorkflowConfig.from_yaml(
            """
            name: A workflow*  *with* *asterisks
            dataset: microsoft/test-dataset

            jobs:
                test,job:
                    tasks:
                    - id: test-task
                    image_key: ingest-prod
                    task: tests.test_submit.MockTask
                    args:
                        hello: world
        """
        )


def test_job_get_dependencies():
    assert (
        WorkflowConfig.from_yaml(
            """
            name: A workflow*  *with* *asterisks
            dataset: microsoft/test-dataset

            jobs:
                test-job:
                    needs: job1
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
        """
        )
        .jobs["test-job"]
        .get_dependencies()
        == ["job1"]
    )

    assert (
        WorkflowConfig.from_yaml(
            """
            name: A workflow*  *with* *asterisks
            dataset: microsoft/test-dataset

            jobs:
                test-job:
                    needs:
                      - job1
                      - job2
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
        """
        )
        .jobs["test-job"]
        .get_dependencies()
        == ["job1", "job2"]
    )
