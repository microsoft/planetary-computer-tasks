from abc import ABC, abstractmethod
from typing import Any, Dict

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.task import TaskRunMessage
from pctasks.execute.models import TaskPollResult, TaskSubmitMessage
from pctasks.execute.settings import ExecutorSettings


class Executor(ABC):
    @abstractmethod
    def submit(
        self,
        submit_msg: TaskSubmitMessage,
        run_msg: TaskRunMessage,
        task_input_blob_config: BlobConfig,
        settings: ExecutorSettings,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def poll_task(
        self,
        executor_id: Dict[str, Any],
        previous_poll_count: int,
        settings: ExecutorSettings,
    ) -> TaskPollResult:
        pass
