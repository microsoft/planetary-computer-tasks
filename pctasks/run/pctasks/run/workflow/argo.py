from pctasks.core.models.record import WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.argo.client import ArgoClient
from pctasks.run.settings import RunSettings
from pctasks.run.workflow.base import WorkflowRunner


class ArgoWorkflowRunner(WorkflowRunner):
    def __init__(self, settings: RunSettings):
        super().__init__(settings)

    def submit_workflow(self, workflow: WorkflowSubmitMessage) -> WorkflowSubmitResult:
        argo_host = self.settings.argo_host
        argo_token = self.settings.argo_token
        runner_image = self.settings.workflow_runner_image

        if not argo_host:
            raise ValueError("Argo host not configured")
        if not argo_token:
            raise ValueError("Argo token not configured")
        if not runner_image:
            raise ValueError("Workflow runner image not configured")

        argo_client = ArgoClient(
            host=argo_host, token=argo_token, namespace=self.settings.argo_namespace
        )

        try:
            _ = argo_client.submit_workflow(
                workflow,
                run_settings=self.settings,
                runner_image=runner_image,
            )
        except Exception as e:
            return WorkflowSubmitResult(
                dataset=workflow.workflow.get_dataset_id(),
                run_id=workflow.run_id,
                status=WorkflowRunStatus.FAILED,
                errors=[str(e)],
            )

        return WorkflowSubmitResult(
            dataset=workflow.workflow.get_dataset_id(),
            run_id=workflow.run_id,
            status=WorkflowRunStatus.RUNNING,
        )
