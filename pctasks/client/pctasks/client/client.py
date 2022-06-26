import io
import logging
import os
import pathlib
import zipfile
from time import perf_counter
from typing import Any, Dict, List, Optional, Union

import requests
from requests import HTTPError

from pctasks.client.errors import (
    JobNotFoundError,
    TaskNotFoundError,
    WorkflowNotFoundError,
)
from pctasks.client.settings import ClientSettings
from pctasks.core.models.api import (
    JobRunResponse,
    JobRunsResponse,
    LinkRel,
    TaskRunResponse,
    TaskRunsResponse,
    UploadCodeResult,
    WorkflowRunResponse,
    WorkflowRunsResponse,
)
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import (
    WorkflowConfig,
    WorkflowSubmitMessage,
    WorkflowSubmitResult,
)

logger = logging.getLogger(__name__)

# Submit
RUN_WORKFLOW_ROUTE = "submit/"
UPLOAD_CODE_ROUTE = "code/upload/"

# Records
LIST_RUNS_ROUTE = "runs/"
FETCH_RUN_ROUTE = "runs/{run_id}"
LIST_JOBS_ROUTE = "runs/{run_id}/jobs/"
FETCH_JOB_ROUTE = "runs/{run_id}/jobs/{job_id}"
LIST_TASKS_ROUTE = "runs/{run_id}/jobs/{job_id}/tasks/"
FETCH_TASK_ROUTE = "runs/{run_id}/jobs/{job_id}/tasks/{task_id}"


class PCTasksClient:
    def __init__(self, settings: Optional[ClientSettings] = None) -> None:
        self.settings = settings or ClientSettings.get()

    def _call_api(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Call the PCTasks API.

        If path is a full URL that matches the API (e.g. from a link href),
        use that URL directly.
        """
        url = (
            path
            if path.startswith(self.settings.endpoint)
            else os.path.join(self.settings.endpoint, path)
        )

        resp = requests.request(
            method,
            url,
            headers={"X-API-KEY": self.settings.api_key},
            **kwargs,
        )

        resp.raise_for_status()
        return resp.json()

    def upload_code(self, local_path: Union[pathlib.Path, str]) -> UploadCodeResult:
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
            file_obj.seek(0)

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
                blob_uri = self.upload_code(local_path).uri
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

    def get_workflows(
        self, dataset_id: Optional[str] = None
    ) -> List[WorkflowRunResponse]:
        route = LIST_RUNS_ROUTE
        if dataset_id:
            route += f"?dataset={dataset_id}"
        result = self._call_api("GET", route)
        return WorkflowRunsResponse.parse_obj(result).runs

    def get_workflow(
        self, run_id: str, dataset_id: Optional[str] = None
    ) -> WorkflowRunResponse:
        route = FETCH_RUN_ROUTE.format(run_id=run_id)
        if dataset_id:
            route += f"?dataset={dataset_id}"
        try:
            result = self._call_api("GET", route)
            return WorkflowRunResponse.parse_obj(result)
        except HTTPError as e:
            if e.response.status_code == 404:
                raise WorkflowNotFoundError(run_id) from e
            raise

    def get_jobs(self, run_id: str) -> List[JobRunResponse]:
        route = LIST_JOBS_ROUTE.format(run_id=run_id)
        result = self._call_api("GET", route)
        return JobRunsResponse.parse_obj(result).jobs

    def get_jobs_from_workflow(
        self, workflow: WorkflowRunResponse
    ) -> List[JobRunResponse]:
        if workflow.links:
            result: List[JobRunResponse] = []
            for link in workflow.links:
                if link.rel == LinkRel.JOB:
                    result.append(
                        JobRunResponse.parse_obj(self._call_api("GET", link.href))
                    )
            return result
        else:
            return self.get_jobs(workflow.run_id)

    def get_job(self, run_id: str, job_id: str) -> JobRunResponse:
        route = FETCH_JOB_ROUTE.format(run_id=run_id, job_id=job_id)
        result = self._call_api("GET", route)
        try:
            return JobRunResponse.parse_obj(result)
        except HTTPError as e:
            if e.response.status_code == 404:
                raise JobNotFoundError(f"Job {job_id} for workflow run {run_id}") from e
            raise

    def get_tasks(self, run_id: str, job_id: str) -> List[TaskRunResponse]:
        route = LIST_TASKS_ROUTE.format(run_id=run_id, job_id=job_id)
        result = self._call_api("GET", route)
        return TaskRunsResponse.parse_obj(result).tasks

    def get_tasks_from_job(self, job: JobRunResponse) -> List[TaskRunResponse]:
        if job.links:
            result: List[TaskRunResponse] = []
            for link in job.links:
                if link.rel == LinkRel.TASK:
                    result.append(
                        TaskRunResponse.parse_obj(self._call_api("GET", link.href))
                    )
            return result
        else:
            return self.get_tasks(job.run_id, job.job_id)

    def get_task(self, run_id: str, job_id: str, task_id: str) -> TaskRunResponse:
        route = FETCH_TASK_ROUTE.format(run_id=run_id, job_id=job_id, task_id=task_id)
        try:
            result = self._call_api("GET", route)
        except HTTPError as e:
            if e.response.status_code == 404:
                raise TaskNotFoundError(
                    f"Task {task_id} of job {job_id} for workflow run {run_id}"
                )
            raise
        return TaskRunResponse.parse_obj(result)

    def get_task_logs_from_task(self, task: TaskRunResponse) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if not task.links:
            return result

        log_links = [link for link in task.links if link.rel == LinkRel.LOG]

        if not log_links:
            return result

        for log_link in log_links:
            resp = requests.get(
                log_link.href, headers={"X-API-KEY": self.settings.api_key}
            )
            resp.raise_for_status()
            result[pathlib.Path(log_link.href).name] = resp.content.decode("utf-8")
        return result

    def get_task_logs(
        self, run_id: str, job_id: str, task_id: str, log_name: Optional[str]
    ) -> Dict[str, str]:

        return self.get_task_logs_from_task(self.get_task(run_id, job_id, task_id))
