from pctasks.core.storage import StorageFactory
from pctasks.task.context import TaskContext


class MockTaskContext(TaskContext):
    """Mock TaskContext for use in task tests."""

    @classmethod
    def default(cls) -> "MockTaskContext":
        return MockTaskContext(
            storage_factory=StorageFactory(),
        )
