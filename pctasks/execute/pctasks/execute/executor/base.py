from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from pctasks.execute.models import (
    FailedSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulSubmitResult,
    TaskPollResult,
)
from pctasks.execute.settings import ExecutorSettings


class TaskExecutor(ABC):
    @abstractmethod
    def submit(
        self,
        prepared_tasks: List[PreparedTaskSubmitMessage],
        settings: ExecutorSettings,
    ) -> List[Union[SuccessfulSubmitResult, FailedSubmitResult]]:
        pass

    @abstractmethod
    def poll_task(
        self,
        executor_id: Dict[str, Any],
        previous_poll_count: int,
        settings: ExecutorSettings,
    ) -> TaskPollResult:
        pass
