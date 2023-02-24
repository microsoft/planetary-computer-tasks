import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import requests

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import TaskDefinition
from pctasks.run.constants import MAX_MISSING_POLLS
from pctasks.run.models import (
    FailedTaskSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskPollResult,
)
from pctasks.run.task.base import TaskRunner

logger = logging.getLogger(__name__)


class LocalTaskRunner(TaskRunner):
    """A local development task runner.

    This submits the run arguments to the local dev endpoint task runner.
    See the local-dev-endpoints service in the development environment.
    """

    def __init__(self, local_dev_endpoints_url: str) -> None:
        self.local_dev_endpoints_url = local_dev_endpoints_url

    def __enter__(self) -> "LocalTaskRunner":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def prepare_task_info(
        self,
        dataset_id: str,
        run_id: str,
        job_id: str,
        task_def: TaskDefinition,
        image: str,
        task_tags: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        return {}

    def submit_tasks(
        self, prepared_tasks: List[PreparedTaskSubmitMessage]
    ) -> List[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]]:
        results: List[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]] = []
        for prepared_task in prepared_tasks:
            task_input_blob_config = prepared_task.task_input_blob_config
            task_tags = prepared_task.task_data.tags
            args = [
                "task",
                "run",
                task_input_blob_config.uri,
                "--sas-token",
                task_input_blob_config.sas_token,
            ]

            if task_input_blob_config.account_url:
                args.extend(["--account-url", task_input_blob_config.account_url])

            data = json.dumps({"args": args, "tags": task_tags or {}}).encode("utf-8")
            resp = requests.post(self.local_dev_endpoints_url + "/execute", data=data)
            if resp.status_code == 200:
                results.append(SuccessfulTaskSubmitResult(task_runner_id=resp.json()))
            else:
                results.append(
                    FailedTaskSubmitResult(errors=[f"{resp.status_code}: {resp.text}"])
                )

        return results

    def poll_task(
        self,
        runner_id: Dict[str, Any],
        previous_poll_count: int,
    ) -> TaskPollResult:
        try:
            resp = requests.get(
                self.local_dev_endpoints_url + f"/poll/{runner_id['id']}"
            )
            if resp.status_code == 200:
                return TaskPollResult.parse_obj(resp.json())
            elif resp.status_code == 404:
                if previous_poll_count < MAX_MISSING_POLLS:
                    return TaskPollResult(task_status=TaskRunStatus.PENDING)
                else:
                    return TaskPollResult(
                        task_status=TaskRunStatus.FAILED,
                        poll_errors=[
                            f"Task not found after {previous_poll_count} polls."
                        ],
                    )
            else:
                resp.raise_for_status()
                raise Exception(f"Unexpected status code: {resp.status_code}")
        except Exception as e:
            logger.exception(e)
            return TaskPollResult(task_status=TaskRunStatus.FAILED)

    def get_failed_tasks(
        self,
        runner_ids: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Dict[str, str]]:
        # TODO: Optimize implementation
        result: Dict[str, Dict[str, str]] = defaultdict(dict)

        for partition_id in runner_ids:
            for task_id, runner_id in runner_ids[partition_id].items():
                poll_result = self.poll_task(runner_id, 0)
                if poll_result.task_status == TaskRunStatus.FAILED:
                    error = (
                        poll_result.poll_errors[0]
                        if poll_result.poll_errors
                        else "Local task failed."
                    )
                    result[partition_id][task_id] = error

        return result

    def cancel_task(self, runner_id: Dict[str, Any]) -> None:
        # No-op
        pass

    def cleanup(self, task_infos: List[Dict[str, Any]]) -> None:
        pass
