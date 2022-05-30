from pctasks.core.models.workflow import WorkflowSubmitMessage


class BatchRunner:
    """Run a RemoteRunner on Azure Batch"""

    def submit_workflow(self, workflow_submit_message: WorkflowSubmitMessage) -> None:
        ...
