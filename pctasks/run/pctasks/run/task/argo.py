import logging
from typing import Any, Dict, List, Optional, Set, Union

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import TaskDefinition
from pctasks.core.utils import map_opt
from pctasks.run.argo.client import ArgoClient
from pctasks.run.constants import MAX_MISSING_POLLS
from pctasks.run.models import (
    FailedTaskSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskPollResult,
)
from pctasks.run.settings import RunSettings
from pctasks.run.task.base import TaskRunner

logger = logging.getLogger(__name__)


class ArgoTaskRunner(TaskRunner):
    def __init__(self, settings: RunSettings):
        self.settings = settings

        argo_host = settings.argo_host
        argo_token = settings.argo_token

        if not argo_host:
            raise Exception("Missing Argo host setting.")

        if not argo_token:
            raise Exception("Missing Argo token setting.")

        self.argo_client = ArgoClient(
            host=argo_host, token=argo_token, namespace=settings.argo_namespace
        )

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
            try:
                task_id = self.argo_client.submit_task(prepared_task, self.settings)
                results.append(SuccessfulTaskSubmitResult(task_runner_id=task_id))
            except Exception as e:
                logger.exception(e)
                results.append(FailedTaskSubmitResult(errors=[str(e)]))

        return results

    def poll_task(
        self, runner_id: Dict[str, Any], previous_poll_count: int
    ) -> TaskPollResult:
        namespace, name = runner_id["namespace"], runner_id["name"]
        task_status_result = self.argo_client.get_task_status(
            namespace=namespace, argo_workflow_name=name
        )

        if task_status_result is None:
            if previous_poll_count < MAX_MISSING_POLLS:
                return TaskPollResult(task_status=TaskRunStatus.PENDING)
            else:
                return TaskPollResult(
                    task_status=TaskRunStatus.FAILED,
                    poll_errors=[f"Task not found after {previous_poll_count} polls."],
                )
        else:
            task_status, error_message = task_status_result
            return TaskPollResult(
                task_status=task_status,
                poll_errors=map_opt(lambda e: [e], error_message),
            )

    def get_failed_tasks(
        self,
        runner_ids: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Set[str]]:
        # TODO: Optimize implementation
        return {
            partition_id: set(
                [
                    task_id
                    for task_id, runner_id in task_map.items()
                    if self.poll_task(runner_id, 0).task_status == TaskRunStatus.FAILED
                ]
            )
            for partition_id, task_map in runner_ids.items()
        }

    def cancel_task(self, runner_id: Dict[str, Any]) -> None:
        namespace, name = runner_id["namespace"], runner_id["name"]
        self.argo_client.terminate_workflow(
            namespace=namespace, argo_workflow_name=name
        )

    def cleanup(self, task_infos: List[Dict[str, Any]]) -> None:
        pass
