from unittest.mock import Mock
from uuid import uuid4

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.task import TaskConfig, TaskRunMessage
from pctasks.core.storage import read_text
from pctasks.dev.queues import TempQueue
from pctasks.execute.models import TaskSubmitMessage
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.submit import submit_task


def test_process_submit_message():
    executor = Mock()
    executor.submit = Mock(return_value={"foo": "bar"})

    run_id = uuid4().hex

    submit_msg = TaskSubmitMessage(
        dataset=DatasetIdentifier(name="test-dataset-id"),
        instance_id="test_instance_id",
        job_id="job-id",
        run_id=run_id,
        config=TaskConfig(
            id="submit_unit_test",
            image="pctasks-ingest:latest",
            task="tests.test_submit.MockTask",
            args={"hello": "world"},
        ),
    )

    settings = ExecutorSettings.get()

    # Use tmp queue to avoid triggering
    # the dev execute_func
    tmp_queue = TempQueue()
    settings.signal_queue_account_name = tmp_queue.queue_config.queue_name
    with tmp_queue:
        _ = submit_task(
            submit_msg=submit_msg,
            settings=settings,
            executor=executor,
        )

        executor.submit.assert_called_once()
        input_blob_config: BlobConfig = executor.submit.call_args.kwargs[
            "task_input_blob_config"
        ]

        input_str = read_text(
            input_blob_config.uri,
            sas_token=input_blob_config.sas_token,
            account_url=settings.blob_account_url,
        )
        run_msg = TaskRunMessage.decode(input_str)

        assert run_msg.args == submit_msg.config.args
