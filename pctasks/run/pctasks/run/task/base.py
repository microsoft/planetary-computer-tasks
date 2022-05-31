from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from pctasks.run.models import (
    FailedSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulSubmitResult,
    TaskPollResult,
)
from pctasks.run.settings import RunSettings


class TaskRunner(ABC):
    def __init__(self, settings: RunSettings):
        self.settings = settings

    @abstractmethod
    def submit_tasks(
        self, prepared_tasks: List[PreparedTaskSubmitMessage]
    ) -> List[Union[SuccessfulSubmitResult, FailedSubmitResult]]:
        pass

    @abstractmethod
    def poll_task(
        self, runner_id: Dict[str, Any], previous_poll_count: int
    ) -> TaskPollResult:
        pass
