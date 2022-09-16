from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar, Union

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, TaskResult, WaitTaskResult
from pctasks.task.context import TaskContext

T = TypeVar("T", bound=PCBaseModel)
U = TypeVar("U", bound=PCBaseModel)


class Task(ABC, Generic[T, U]):
    """Task[T, U] is the base class for all tasks to be executed by PCTasks.

    To create a new task, subclass Task with T as the input model (a Pydantic mode)
    and U as the output model (also a Pydantic model). The only other requirement
    is to implement the run method, which takes the input model and a TaskContext
    and returns either an instance of the output model, a WaitTaskResult, or a
    FailedTaskResult.

    You can also define what environment variables are required to run the task
    through overriding the get_required_environment_variables method. This will
    ensure that the task will not be run if the environment variables are not
    set as part of the task configuration.
    """

    _input_model: Type[T]
    _output_model: Type[U]

    def __init__(self, *args: Any, **kwargs: Any):
        if not getattr(self, "_input_model", None):
            raise NotImplementedError(
                "_input_model must be defined. "
                "Define on Task child class as a class attribute."
            )
        if not getattr(self, "_output_model", None):
            raise NotImplementedError(
                "_output_model must be defined. "
                "Define on Task child class as a class attribute."
            )

    def get_required_environment_variables(self) -> List[str]:
        return []

    @abstractmethod
    def run(
        self, input: T, context: TaskContext
    ) -> Union[U, WaitTaskResult, FailedTaskResult]:
        pass

    def parse_and_run(self, data: Dict[str, Any], context: TaskContext) -> TaskResult:
        args = self._input_model.parse_obj(data)
        output = self.run(args, context)

        if isinstance(output, WaitTaskResult):
            return output
        elif isinstance(output, FailedTaskResult):
            return output
        else:
            return TaskResult.completed(output=output.dict())
