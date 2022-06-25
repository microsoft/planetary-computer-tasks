import io
import logging
import os
import pathlib
import zipfile
from time import perf_counter
from typing import Any, Dict

import requests

from pctasks.client.settings import ClientSettings
from pctasks.core.models.api import UploadCodeResult
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import (
    WorkflowConfig,
    WorkflowSubmitMessage,
    WorkflowSubmitResult,
)

logger = logging.getLogger(__name__)


RUN_WORKFLOW_ROUTE = "submit/"
UPLOAD_CODE_ROUTE = "code/upload/"


class PCTasksClient:
    def __init__(self, settings: ClientSettings) -> None:
        self.settings = settings

    def _call_api(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Call the PCTasks API.
        """
        resp = requests.request(
            method,
            os.path.join(self.settings.endpoint, path),
            headers={"X-API-KEY": self.settings.api_key},
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    def _upload_code(self, local_path: str) -> UploadCodeResult:
        """Upload a file to Azure Blob Storage.

        Returns the blob URI.
        """
        path = pathlib.Path(local_path)

        if not path.exists():
            raise OSError(f"Path {path} does not exist.")

        if path.is_file():
            file_obj = path.open("rb")
            name = path.name

        else:
            file_obj = io.BytesIO()
            with zipfile.PyZipFile(file_obj, "w") as zf:
                zf.writepy(str(path))

            name = path.with_suffix(".zip").name

        try:
            resp = self._call_api(
                "POST", UPLOAD_CODE_ROUTE, files={"file": (name, file_obj)}
            )
        finally:
            file_obj.close()

        return UploadCodeResult(**resp)

    def _submit_workflow(self, message: WorkflowSubmitMessage) -> WorkflowSubmitResult:
        resp = self._call_api("POST", RUN_WORKFLOW_ROUTE, data=message.json())
        return WorkflowSubmitResult(**resp)

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

        Handles both `file` and `requirements` files.
        """
        local_path_to_blob: Dict[str, Dict[str, str]] = {"src": {}, "requirements": {}}

        def _uploaded_path(local_path: str, cache_key: str) -> str:
            blob_uri = local_path_to_blob[cache_key].get(local_path)
            if blob_uri is None:
                blob_uri = self._upload_code(local_path).uri
                local_path_to_blob["src"][local_path] = blob_uri
            return blob_uri

        for job_config in workflow.jobs.values():
            for task_config in job_config.tasks:
                if task_config.code:
                    if task_config.code.src:
                        task_config.code.src = _uploaded_path(
                            task_config.code.src, "src"
                        )
                    if task_config.code.requirements:
                        task_config.code.requirements = _uploaded_path(
                            task_config.code.requirements, "requirements"
                        )

    def submit_workflow(self, message: WorkflowSubmitMessage) -> WorkflowSubmitMessage:
        """Submits a workflow for processing.

        Returns a modified :class:`WorkflowSubmitMessage` that has
        a ``run_id`` set.
        """
        message = message.copy(deep=True)

        for job in message.workflow.jobs.values():
            for task in job.tasks:
                self._transform_task_config(task)

        # Inline args
        message.workflow = message.get_workflow_with_templated_args()

        logger.debug("Uploading code...")
        start = perf_counter()
        self._transform_workflow_code(message.workflow)
        end = perf_counter()
        logger.debug(f"Uploading code took {end - start:.2f} seconds.")

        logger.debug("Submitting workflow...")
        start = perf_counter()
        result = self._submit_workflow(message)
        end = perf_counter()
        logger.debug(f"Submit took {end - start:.2f} seconds.")
        logger.debug(result.json(indent=2))

        return message
