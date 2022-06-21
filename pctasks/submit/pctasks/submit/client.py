import logging
from time import perf_counter
from typing import Any, Optional, Tuple

from azure.identity import DefaultAzureCredential
from azure.storage.queue import (
    BinaryBase64DecodePolicy,
    BinaryBase64EncodePolicy,
    QueueClient,
    QueueServiceClient,
)

from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.core.models.operation import OperationSubmitMessage
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import WorkflowConfig, WorkflowSubmitMessage
from pctasks.submit.settings import SubmitSettings
from pctasks.submit.code_uploader import upload_code

logger = logging.getLogger(__name__)


def _get_queue_client(
    settings: SubmitSettings,
) -> Tuple[QueueServiceClient, QueueClient]:
    service_client: QueueServiceClient

    queue_name = settings.queue_name
    if settings.connection_string:
        service_client = QueueServiceClient.from_connection_string(
            settings.connection_string
        )
    else:
        account_url = settings.get_submit_queue_url()
        credential: Optional[str] = settings.account_key or settings.sas_token
        service_client = QueueServiceClient(
            account_url,
            credential=credential or DefaultAzureCredential(),
        )

    return (
        service_client,
        service_client.get_queue_client(
            queue_name,
            message_encode_policy=BinaryBase64EncodePolicy(),
            message_decode_policy=BinaryBase64DecodePolicy(),
        ),
    )


class SubmitClient:
    def __init__(self, settings: SubmitSettings) -> None:
        self.settings = settings
        self.service_client: Optional[QueueServiceClient] = None
        self.queue_client: Optional[QueueClient] = None

    def __enter__(self) -> "SubmitClient":
        self.service_client, self.queue_client = _get_queue_client(self.settings)

        return self

    def get_queue_name(self) -> str:
        if not self.service_client:
            raise RuntimeError("SubmitClient is not opened. Use as a context manager.")
        return f"{self.service_client.account_name}/{self.settings.queue_name}"

    def __exit__(self, *args: Any) -> None:
        if self.queue_client:
            self.queue_client.close()
            self.queue_client = None
        if self.service_client:
            self.service_client.close()
            self.service_client = None

    def _transform_task_config(self, task_config: TaskConfig) -> None:
        # Replace image keys with configured images.
        if task_config.image_key:
            image_config = self.settings.image_keys.get(task_config.image_key)
            if image_config:
                logger.debug(
                    f"Setting image to '{image_config.image}' from settings..."
                )
                task_config.image = image_config.image
                task_config.image_key = None
                task_config.environment = image_config.merge_env(
                    task_config.environment
                )

    def _transform_workflow_code(self, workflow: WorkflowConfig) -> None:
        """
        Handle runtime code availability.

        Code files specified in the tasks are uploaded to our Azure Blob Storage.
        The Task code paths are rewritten to point to the newly uploaded files.
        """
        local_path_to_blob = {}

        for job_config in workflow.jobs.values():
            for task_config in job_config.tasks:
                if task_config.code and task_config.code in local_path_to_blob:
                    # already uploaded from a previous task
                    task_config.code = local_path_to_blob[task_config.code]
                elif task_config.code:
                    storage_path = upload_code(task_config.code, self.settings)
                    logger.warning("Uploaded %s to %s", task_config.code, storage_path)
                    local_path_to_blob[storage_path] = task_config.code = storage_path

    def submit_workflow(self, message: WorkflowSubmitMessage) -> str:
        """Submits a workflow for processing.

        Returns the run ID associated with this submission, which
        was either set on the message or from the Queue submission.
        """
        if not self.queue_client:
            raise RuntimeError("SubmitClient is not opened. Use as a context manager.")

        for job in message.workflow.jobs.values():
            for task in job.tasks:
                self._transform_task_config(task)

        logger.debug("Uploading code...")
        start = perf_counter()
        self._transform_workflow_code(message.workflow)
        end = perf_counter()
        logger.debug(f"Uploading code took {end - start:.2f} seconds.")
 
        logger.debug("Submitting workflow...")
        start = perf_counter()
        _ = self.queue_client.send_message(message.json(exclude_none=True).encode())
        end = perf_counter()
        logger.debug(f"Submit took {end - start:.2f} seconds.")
        return message.run_id

    def submit_notification(self, message: NotificationSubmitMessage) -> str:
        """Submits a NotificationMessage for processing.

        Returns the run ID associated with this submission, which
        was either set on the message or from the Queue submission.
        """
        if not self.queue_client:
            raise RuntimeError("SubmitClient is not opened. Use as a context manager.")

        logger.debug("Submitting notification...")
        start = perf_counter()
        _ = self.queue_client.send_message(message.json(exclude_none=True).encode())
        end = perf_counter()
        logger.debug(f"Submit took {end - start:.2f} seconds.")
        return str(message.processing_id.run_id)

    def submit_operation(self, message: OperationSubmitMessage) -> str:
        ...
