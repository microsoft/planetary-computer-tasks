from dataclasses import dataclass

from pctasks.core.models.task import TaskRunConfig
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens


@dataclass
class TaskContext:
    storage_factory: StorageFactory
    run_id: str

    @classmethod
    def from_task_run_config(cls, task_config: TaskRunConfig) -> "TaskContext":
        return cls(
            storage_factory=StorageFactory(Tokens(task_config.tokens)),
            run_id=task_config.run_id,
        )
