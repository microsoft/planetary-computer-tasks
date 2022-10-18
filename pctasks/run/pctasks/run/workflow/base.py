from abc import ABC, abstractmethod

from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.settings import RunSettings, WorkflowExecutorConfig


class WorkflowRunner(ABC):
    def __init__(self, run_settings: RunSettings, cosmosdb_settings: CosmosDBSettings):
        self.run_settings = run_settings
        self.cosmosdb_settings = cosmosdb_settings

    def get_executor_config(self) -> WorkflowExecutorConfig:
        return WorkflowExecutorConfig(
            run_settings=self.run_settings, cosmosdb_settings=self.cosmosdb_settings
        )

    @abstractmethod
    def submit_workflow(
        self, submit_msg: WorkflowSubmitMessage
    ) -> WorkflowSubmitResult:
        pass
