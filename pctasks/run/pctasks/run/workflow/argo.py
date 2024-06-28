from pctasks.core.models.run import WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.argo.client import ArgoClient
from pctasks.run.workflow.base import WorkflowRunner


class ArgoWorkflowRunner(WorkflowRunner):
    def submit_workflow(
        self, submit_msg: WorkflowSubmitMessage
    ) -> WorkflowSubmitResult:
        print("Argo worflow runner", flush=True)
        argo_host = self.run_settings.argo_host
        argo_token = self.run_settings.argo_token
        runner_image = self.run_settings.workflow_runner_image

        if not argo_host:
            raise ValueError("Argo host not configured")
        if not argo_token:
            raise ValueError("Argo token not configured")
        if not runner_image:
            raise ValueError("Workflow runner image not configured")

        argo_client = ArgoClient(
            host=argo_host, token=argo_token, namespace=self.run_settings.argo_namespace
        )

        try:
            print("Submitting the workflow...")
            submit_results = argo_client.submit_workflow(
                submit_msg,
                run_id=submit_msg.run_id,
                executor_config=self.get_executor_config(),
                runner_image=runner_image,
            )
            print(f"Submition results!: {submit_results}", flush=True)
        except Exception as e:
            return WorkflowSubmitResult(
                run_id=submit_msg.run_id,
                status=WorkflowRunStatus.FAILED,
                errors=[str(e)],
            )

        return WorkflowSubmitResult(
            run_id=submit_msg.run_id,
            status=WorkflowRunStatus.RUNNING,
        )
