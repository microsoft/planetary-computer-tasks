from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.run.settings import RunSettings, WorkflowRunnerType
from pctasks.run.workflow.argo import ArgoWorkflowRunner
from pctasks.run.workflow.base import WorkflowRunner
from pctasks.run.workflow.local import LocalWorkflowRunner


def get_workflow_runner() -> WorkflowRunner:
    run_settings = RunSettings.get()
    cosmosdb_settings = CosmosDBSettings.get()

    if run_settings.workflow_runner_type == WorkflowRunnerType.LOCAL:
        assert run_settings.local_dev_endpoints_url  # Checked during validation
        return LocalWorkflowRunner(run_settings, cosmosdb_settings)
    elif run_settings.workflow_runner_type == WorkflowRunnerType.ARGO:
        return ArgoWorkflowRunner(run_settings, cosmosdb_settings)
    else:
        raise ValueError(
            f"Unknown workflow runner type: {run_settings.workflow_runner_type}"
        )
