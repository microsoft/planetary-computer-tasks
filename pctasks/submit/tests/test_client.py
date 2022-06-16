import json
from typing import Any, List

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.core.yaml import model_from_yaml
from pctasks.dev.queues import TempQueue
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings


def test_client_submit():

    test_queue = TempQueue()
    settings = SubmitSettings(
        connection_string=test_queue.queue_config.connection_string,
        queue_name=test_queue.queue_config.queue_name,
    )

    workflow = WorkflowConfig(
        name="Test Workflow!",
        dataset=DatasetIdentifier(owner=MICROSOFT_OWNER, name="test-dataset"),
        jobs={
            "test-job": JobConfig(
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

    submit_message = WorkflowSubmitMessage(
        workflow=workflow,
    )

    with test_queue as read_queue:
        with SubmitClient(settings) as client:
            client.submit_workflow(submit_message)

        messages: List[Any] = list(read_queue.receive_messages())

        assert len(messages) == 1
        message = messages[0]

        body = json.loads(message.content)
        actual_submit_msg = WorkflowSubmitMessage(**body)
        assert submit_message == actual_submit_msg


def test_sets_image_from_configured_key():
    test_queue = TempQueue()
    yaml = f"""
submit:
    connection_string: {test_queue.queue_config.connection_string}
    queue_name: {test_queue.queue_config.queue_name}
    image_keys:
        ingest-staging:
            image: pctasks-ingest:latest
        ingest-prod:
            image: pctasks-ingest:v1
"""

    settings = model_from_yaml(
        SubmitSettings, yaml, section=SubmitSettings.section_name()
    )

    workflow = WorkflowConfig.from_yaml(
        """
    name: A workflow*  *with* *asterisks
    dataset:
        owner: microsoft
        name: test-dataset

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

    with test_queue as read_queue:
        with SubmitClient(settings) as client:
            client.submit_workflow(WorkflowSubmitMessage(workflow=workflow))

        messages: List[Any] = list(read_queue.receive_messages())

    assert len(messages) == 1
    message = messages[0]

    body = json.loads(message.content)
    actual_submit_msg = WorkflowSubmitMessage(**body)
    assert (
        actual_submit_msg.workflow.jobs["test-job"].tasks[0].image
        == "pctasks-ingest:v1"
    )
