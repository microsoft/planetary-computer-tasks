import pytest
from pydantic import ValidationError

from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.workflow import (
    JobDefinition,
    Workflow,
    WorkflowDefinition,
    WorkflowSubmitMessage,
)


def test_sets_job_id():
    workflow = WorkflowDefinition.from_yaml(
        """
        name: A workflow*  *with* *asterisks
        dataset: test-dataset

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
        WorkflowDefinition(
            name="Test Workflow!",
            dataset_id="test-dataset",
            jobs={
                "A job / task / thing": JobDefinition(
                    tasks=[
                        TaskDefinition(
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
    dataset: test-dataset

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
    workflow_def = WorkflowDefinition.from_yaml(workflow)
    workflow = Workflow(id="test-workflow", definition=workflow_def)
    submit_message = WorkflowSubmitMessage(
        workflow=workflow, args={"name": "world"}, run_id="test-run"
    )
    templated = submit_message.get_workflow_with_templated_args()
    assert templated.definition.jobs["test-job"].tasks[0].args["hello"] == "world"


def test_unexpected_args():
    workflow = """
    name: Test workflow
    dataset: test-dataset

    args:
      - nombre

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow_def = WorkflowDefinition.from_yaml(workflow)
    workflow = Workflow(id="test-workflow", definition=workflow_def)
    try:
        _ = WorkflowSubmitMessage(
            workflow=workflow,
            args={"nombre": "mundo", "name": "world"},
            run_id="test-run",
        )
    except ValidationError as e:
        assert "Unexpected args" in str(e)
        return


def test_missing_and_unexpected_args():
    workflow = """
    name: Test workflow
    dataset: test-dataset

    args:
      - nombre

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow_def = WorkflowDefinition.from_yaml(workflow)
    workflow = Workflow(id="test-workflow", definition=workflow_def)
    try:
        _ = WorkflowSubmitMessage(
            workflow=workflow, args={"name": "mundo"}, run_id="test-run"
        )
    except ValidationError as e:
        assert "Unexpected args" in str(e)
        assert "Args expected" in str(e)
        return


def test_missing_args():
    workflow = """
    name: Test workflow
    dataset: test-dataset

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
    workflow_def = WorkflowDefinition.from_yaml(workflow)
    workflow = Workflow(id="test-workflow", definition=workflow_def)
    try:
        _ = WorkflowSubmitMessage(workflow=workflow, run_id="test-run")
    except ValidationError as e:
        assert "Args expected" in str(e)
        return


def test_job_ids_no_commas():
    with pytest.raises(ValidationError):
        _ = WorkflowDefinition.from_yaml(
            """
            name: A workflow*  *with* *asterisks
            dataset: test-dataset

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
        WorkflowDefinition.from_yaml(
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
        WorkflowDefinition.from_yaml(
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


def test_validate_streaming_workflow():
    job = JobDefinition(
        tasks=[
            TaskDefinition(id="task-0", task="task", image="na"),
            TaskDefinition(id="task-1", task="task", image="na"),
        ]
    )

    with pytest.raises(ValueError, match="exactly one job."):
        WorkflowDefinition(
            name="name",
            jobs={"a": job, "b": job},
            dataset="test",
            is_streaming=True,
        )

    with pytest.raises(ValueError, match="exactly one task."):
        WorkflowDefinition(
            name="name",
            jobs={"a": job},
            dataset="test",
            is_streaming=True,
        )

    job.tasks.pop()
    # Note: this test is sensitive to the order we validate these properties.
    args = [
        ("queue_url", "https://test.queue.core.windows.net/test"),
        ("visibility_timeout", 100),
        ("min_replica_count", 0),
        ("max_replica_count", 10),
        ("polling_interval", 30),
        ("trigger_queue_length", 100),
    ]
    job.tasks[0].args["streaming_options"] = {}

    for k, v in args:
        with pytest.raises(ValueError, match=k):
            WorkflowDefinition(
                name="name",
                jobs={"a": job},
                dataset="test",
                is_streaming=True,
            )
        job.tasks[0].args["streaming_options"][k] = v

    # and now we have a valid one
    WorkflowDefinition(
        name="name",
        jobs={"a": job},
        dataset="test",
        is_streaming=True,
    )
