from typing import Optional

from pctasks.run.settings import RunSettings, WorkflowRunnerType
from pctasks.run.workflow.argo import ArgoWorkflowRunner
from pctasks.run.workflow.base import WorkflowRunner
from pctasks.run.workflow.local import LocalWorkflowRunner


def get_workflow_runner(settings: Optional[RunSettings] = None) -> WorkflowRunner:
    settings = settings or RunSettings.get()

    if settings.workflow_runner_type == WorkflowRunnerType.LOCAL:
        assert settings.local_executor_url  # Checked during settings validation
        return LocalWorkflowRunner(settings)
    elif settings.workflow_runner_type == WorkflowRunnerType.ARGO:
        return ArgoWorkflowRunner(settings)
    else:
        raise ValueError(
            f"Unknown workflow runner type: {settings.workflow_runner_type}"
        )
