from typing import Optional

from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.run.models import TaskSubmitMessage
from pctasks.run.settings import WorkflowExecutorConfig
from pctasks.run.task.prepare import prepare_task, prepare_task_data
from pctasks.run.workflow import kubernetes


class StreamingWorkflowExecutor:
    """
    Registers a streaming workflow.
    """

    def __init__(self, settings: Optional[WorkflowExecutorConfig] = None) -> None:
        self.config = settings or WorkflowExecutorConfig.get()

    def execute_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> None:
        """'Execute' a workflow by submitting the Kube"""

        workflow_def = submit_message.workflow.definition

        # Get the single task definition. TODO
        job_def = list(workflow_def.jobs.values())[0]
        task_def = job_def.tasks[0]

        dataset_id: str = workflow_def.dataset_id
        run_id: str = submit_message.run_id
        job_id: str = job_def.get_id()
        partition_id: str = "0"

        task_data = prepare_task_data(
            dataset_id,
            run_id,
            job_id,
            task_def,
            settings=self.config.run_settings,
            tokens=workflow_def.tokens,
            target_environment=workflow_def.target_environment,
            task_runner=None,
        )

        task_submit_message = TaskSubmitMessage(
            dataset_id=dataset_id,
            run_id=run_id,
            job_id=job_id,
            partition_id=partition_id,
            tokens=workflow_def.tokens,
            definition=task_def,
            target_environment=workflow_def.target_environment,
        )

        prepared_task = prepare_task(
            task_submit_message,
            run_id,
            task_data=task_data,
            settings=self.config.run_settings,
            generate_sas_tokens=False,
        )

        kubernetes.submit_task(prepared_task, self.config.run_settings)
