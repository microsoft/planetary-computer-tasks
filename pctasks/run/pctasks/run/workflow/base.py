from abc import ABC, abstractmethod

from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.settings import RunSettings


class WorkflowRunner(ABC):
    def __init__(self, settings: RunSettings):
        self.settings = settings

    @abstractmethod
    def submit_workflow(
        self, submit_msg: WorkflowSubmitMessage
    ) -> WorkflowSubmitResult:
        pass
