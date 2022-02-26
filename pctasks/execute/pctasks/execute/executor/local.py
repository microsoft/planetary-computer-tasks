import json
import logging
from typing import Any, Dict

import requests

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import TaskRunMessage
from pctasks.execute.executor.base import Executor
from pctasks.execute.models import TaskPollResult, TaskSubmitMessage
from pctasks.execute.settings import ExecutorSettings

logger = logging.getLogger(__name__)


class LocalExecutor(Executor):
    """A local development executor.

    This submits the run arguments to a local executor.
    See the local-executor service in the development environment.
    """

    def __init__(self, local_executor_url: str):
        self.local_executor_url = local_executor_url

    def submit(
        self,
        submit_msg: TaskSubmitMessage,
        run_msg: TaskRunMessage,
        task_input_blob_config: BlobConfig,
        settings: ExecutorSettings,
    ) -> Dict[str, Any]:
        args = [
            "task",
            "run",
            task_input_blob_config.uri,
            "--sas-token",
            task_input_blob_config.sas_token,
        ]

        if task_input_blob_config.account_url:
            args.extend(["--account-url", task_input_blob_config.account_url])

        data = json.dumps({"args": args}).encode("utf-8")
        resp = requests.post(self.local_executor_url + "/execute", data=data)
        return resp.json()

    def poll_task(
        self,
        executor_id: Dict[str, Any],
        previous_poll_count: int,
        settings: ExecutorSettings,
    ) -> TaskPollResult:
        try:
            resp = requests.get(self.local_executor_url + f"/poll/{executor_id['id']}")
            if resp.status_code == 200:
                return TaskPollResult.parse_obj(resp.json())
            else:
                return TaskPollResult(task_status=TaskRunStatus.PENDING)
        except Exception as e:
            logger.exception(e)
            return TaskPollResult(task_status=TaskRunStatus.FAILED)
