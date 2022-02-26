import inspect
from typing import Optional, TypeVar

from pctasks.core.models.base import PCBaseModel
from pctasks.task.task import Task

T = TypeVar("T", bound=PCBaseModel)
U = TypeVar("U", bound=PCBaseModel)


def get_task_path(task: Task[T, U], name: str, module: Optional[str] = None) -> str:
    """Convenience method for getting the path to a task.

    Detects the module name. Requires the user supply the importable
    variable name, including any containing instances or classes.
    """
    if not module:
        m = inspect.getmodule(task)
        if not m:
            raise ValueError(f"Could not find module for task {task}")
        module = m.__name__
    return f"{module}:{name}"
