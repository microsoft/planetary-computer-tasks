from dataclasses import dataclass

from pctasks.core.models.task import TaskRunConfig
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens


@dataclass
class TaskContext:
    """Context that is passed into Task run methods.

    This class is used to supply the Task with the necessary
    framework components to run.
    """

    storage_factory: StorageFactory
    """A StorageFactory instance configured with workflow tokens"""

    run_id: str
    """The run ID of the workflow currently being executed."""

    @classmethod
    def from_task_run_config(cls, task_config: TaskRunConfig) -> "TaskContext":
        return cls(
            storage_factory=StorageFactory(Tokens(task_config.tokens)),
            run_id=task_config.run_id,
        )
