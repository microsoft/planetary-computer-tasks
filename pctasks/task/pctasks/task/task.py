from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar, Union

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, TaskResult, WaitTaskResult
from pctasks.task.context import TaskContext

T = TypeVar("T", bound=PCBaseModel)
U = TypeVar("U", bound=PCBaseModel)


class Task(ABC, Generic[T, U]):
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
