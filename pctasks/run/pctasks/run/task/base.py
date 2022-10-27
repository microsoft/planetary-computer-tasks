from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pctasks.core.models.task import TaskDefinition
from pctasks.run.models import (
    FailedTaskSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskPollResult,
)
from pctasks.run.settings import RunSettings


class TaskRunner(ABC):
    def __init__(self, settings: RunSettings):
        self.settings = settings

    @abstractmethod
    def prepare_task_info(
        self,
        dataset_id: str,
        run_id: str,
        job_id: str,
        task_def: TaskDefinition,
        image: str,
        task_tags: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def submit_tasks(
        self, prepared_tasks: List[PreparedTaskSubmitMessage]
    ) -> List[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]]:
        pass

    @abstractmethod
    def poll_task(
        self, runner_id: Dict[str, Any], previous_poll_count: int
    ) -> TaskPollResult:
        pass

    @abstractmethod
    def get_failed_tasks(
        self,
        runner_ids: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Dict[str, str]]:
        """Finds failed tasks.

        runner_ids is a dictionary of partition IDs to a
        dictionary of task IDs to runner IDs.

        Returns a dictionary of partition IDs to a
        map of failed task IDs to error messages.
        """
        pass

    @abstractmethod
    def cancel_task(self, runner_id: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def cleanup(self, task_infos: List[Dict[str, Any]]) -> None:
        """Performs any cleanup after tasks have finished running.

        task_infos is a list of dictionaries
        that were returned by prepare_task_info.
        """
        pass
