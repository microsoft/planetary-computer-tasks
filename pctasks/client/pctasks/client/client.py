import io
import logging
import os
import pathlib
from time import perf_counter
from typing import Any, Dict, Iterable, Optional, Type, TypeVar, Union
from urllib.parse import urlparse

import requests
from requests import HTTPError
from rich.prompt import Confirm

from pctasks.client.errors import (
    ConfirmationError,
    NoWorkflowIDError,
    WorkflowExistsError,
    WorkflowNotFoundError,
)
from pctasks.client.settings import ClientSettings
from pctasks.core.importer import write_code
from pctasks.core.models.record import Record
from pctasks.core.models.response import (
    JobPartitionRunRecordListResponse,
    JobPartitionRunRecordResponse,
    RecordListResponse,
    UploadCodeResult,
    WorkflowRecordListResponse,
    WorkflowRecordResponse,
    WorkflowRunRecordListResponse,
    WorkflowRunRecordResponse,
)
from pctasks.core.models.run import JobPartitionRunRecord, WorkflowRunRecord
from pctasks.core.models.workflow import (
    Workflow,
    WorkflowDefinition,
    WorkflowRecord,
    WorkflowSubmitRequest,
    WorkflowSubmitResult,
)
from pctasks.core.utils import map_opt
from pctasks.core.utils.backoff import with_backoff

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Record)

# Submit
UPLOAD_CODE_ROUTE = "code/upload"

# Workflow
LIST_WORKFLOWS_ROUTE = "workflows"  # GET
WORKFLOW_ROUTE = "workflows/{workflow_id}"  # POST / GET / PUT / DELETE
SUBMIT_WORKFLOW_ROUTE = "workflows/{workflow_id}/submit"  # POST
LIST_WORKFLOW_RUNS_ROUTE = "workflows/{workflow_id}/runs"  # GET

# Runs
FETCH_WORKFLOW_RUN_ROUTE = "runs/{run_id}"
FETCH_WORKFLOW_RUN_LOG_ROUTE = "runs/{run_id}/log"
LIST_JOB_PARTITION_RUNS_ROUTE = "runs/{run_id}/jobs/{job_id}/partitions"
FETCH_JOB_PARTITION_RUN_ROUTE = "runs/{run_id}/jobs/{job_id}/partitions/{partition_id}"
FETCH_TASK_RUN_LOG_ROUTE = (
    "runs/{run_id}/jobs/{job_id}/partitions/{partition_id}/tasks/{task_id}/log"
)


class PCTasksClient:
    def __init__(self, settings: Optional[ClientSettings] = None) -> None:
        self.settings = settings or ClientSettings.get()

    def _call_api_resp(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Call the PCTasks API.

        If path is a full URL that matches the API (e.g. from a link href),
        use that URL directly.
        """
        params = map_opt(
            lambda p: {k: v for k, v in p.items() if v is not None}, params
        )
        url = (
            path
            if path.startswith(self.settings.endpoint)
            else os.path.join(self.settings.endpoint, path)
        )

        def do_request() -> requests.Response:
            if self.settings.access_key:
                headers = {
                    "X-Access-Key": self.settings.access_key,
                    "X-Has-Authorization": "true",
                    "X-Has-Subscription": "true",
                    "X-User-Email": "pctasks@microsoft.com",
                }
            else:
                headers = {"X-API-KEY": self.settings.api_key}

            resp = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                **kwargs,
            )
            logger.debug(f"API request: {method} {url}")
            logger.debug(f"API response: {resp.status_code}")
            logger.debug(f"API response: {resp.text}")
            resp.raise_for_status()
            return resp

        resp = with_backoff(do_request)
        return resp

    def _call_api_text(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        resp = self._call_api_resp(method, path, params, **kwargs)
        return resp.content.decode("utf-8")

    def _call_api(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        resp = self._call_api_resp(method, path, params, **kwargs)
        return resp.json()

    def _confirm(self, op_name: str, auto_confirm: bool) -> None:
        if auto_confirm:
            return

        if self.settings.confirmation_required:
            confirmed = Confirm.ask(
                f"Send '{op_name}' request to {self.settings.endpoint}?"
            )
            if not confirmed:
                raise ConfirmationError(f"'{op_name}' request cancelled.")

    def _yield_page_results(
        self,
        route: str,
        record_list_response_type: Type[RecordListResponse[T]],
        page_token: Optional[str] = None,
        page_limit: Optional[int] = None,
        max_pages: Optional[int] = None,
        sort_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> Iterable[T]:
        result: Optional[RecordListResponse[T]] = None
        page_count = 0
        params: Dict[str, Any] = {
            "pageLimit": page_limit or self.settings.default_page_size,
            "pageToken": page_token,
        }
        if sort_by is not None:
            params["sortBy"] = sort_by
            if descending is not None:
                params["desc"] = descending
        while (
            result is None
            or result.next_page_token
            or (max_pages is not None and page_count <= max_pages)
        ):
            resp = self._call_api(
                "GET",
                route,
                params=params,
            )
            result = record_list_response_type.parse_obj(resp)
            yield from result.records
            page_count += 1
            page_token = result.next_page_token
            params["pageToken"] = page_token

    # ## CODE ##

    def upload_code(self, local_path: Union[pathlib.Path, str]) -> UploadCodeResult:
        """Upload a file to Azure Blob Storage.

        Returns the blob URI.
        """
        path = pathlib.Path(local_path)

        if not path.exists():
            raise OSError(f"Path {path} does not exist.")

        file_obj: Union[io.BufferedReader, io.BytesIO]
        name, file_obj = write_code(path)

        try:
            resp = self._call_api(
                "POST", UPLOAD_CODE_ROUTE, files={"file": (name, file_obj)}
            )
        finally:
            file_obj.close()

        return UploadCodeResult(**resp)

    def _upload_code(self, workflow: WorkflowDefinition) -> None:
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
                local_path_to_blob[cache_key][local_path] = blob_uri
            return blob_uri

        for job_config in workflow.jobs.values():
            for task_config in job_config.tasks:
                if task_config.code:
                    if task_config.code.src:
                        if not urlparse(task_config.code.src).scheme:
                            task_config.code.src = _uploaded_path(
                                task_config.code.src, "src"
                            )
                    if task_config.code.requirements:
                        if not urlparse(task_config.code.requirements).scheme:
                            task_config.code.requirements = _uploaded_path(
                                task_config.code.requirements, "requirements"
                            )

    # ## WORKFLOWS ##

    def list_workflows(
        self,
        page_limit: Optional[int] = None,
        page_token: Optional[str] = None,
        max_pages: Optional[int] = None,
        sort_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> Iterable[WorkflowRecord]:
        route = LIST_WORKFLOWS_ROUTE
        yield from self._yield_page_results(
            route,
            WorkflowRecordListResponse,
            page_limit=page_limit,
            page_token=page_token,
            max_pages=max_pages,
            sort_by=sort_by,
            descending=descending,
        )

    def create_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: Optional[str] = None,
        auto_confirm: bool = False,
    ) -> None:
        if workflow_id is None:
            if not workflow_definition.workflow_id:
                raise NoWorkflowIDError(
                    "If no workflow ID is specified, "
                    "the workflow definition must have a "
                    "workflow_id field set"
                )
            workflow_id = workflow_definition.workflow_id
        if self.get_workflow(workflow_id):
            raise WorkflowExistsError(f"A workflow with {workflow_id} already exists.")
        workflow = Workflow(
            id=workflow_id,
            definition=workflow_definition,
        )
        self._confirm("create workflow", auto_confirm=auto_confirm)
        self._upsert_workflow(workflow_id, workflow, "POST")

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        try:
            result = self._call_api(
                "GET", WORKFLOW_ROUTE.format(workflow_id=workflow_id)
            )
            return WorkflowRecordResponse.parse_obj(result).record
        except HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def update_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: Optional[str] = None,
        auto_confirm: bool = False,
    ) -> None:
        if workflow_id is None:
            if not workflow_definition.workflow_id:
                raise NoWorkflowIDError(
                    "If no workflow ID is specified, "
                    "the workflow definition must have a "
                    "workflow_id field set"
                )
            workflow_id = workflow_definition.workflow_id
        if not self.get_workflow(workflow_id):
            raise WorkflowNotFoundError(f"No workflow with {workflow_id} found.")
        workflow = Workflow(
            id=workflow_id,
            definition=workflow_definition,
        )
        self._confirm("update workflow", auto_confirm=auto_confirm)
        self._upsert_workflow(workflow_id, workflow, "PUT")

    def upsert_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: Optional[str] = None,
        auto_confirm: bool = False,
    ) -> None:
        if workflow_id is None:
            if not workflow_definition.workflow_id:
                raise NoWorkflowIDError(
                    "If no workflow ID is specified, "
                    "the workflow definition must have a "
                    "workflow_id field set"
                )
            workflow_id = workflow_definition.workflow_id
        if not self.get_workflow(workflow_id):
            workflow = Workflow(
                id=workflow_id,
                definition=workflow_definition,
            )
            self._confirm("create workflow", auto_confirm=auto_confirm)
            self._upsert_workflow(workflow_id, workflow, "POST")
        else:
            workflow = Workflow(
                id=workflow_id,
                definition=workflow_definition,
            )
            self._confirm("update workflow", auto_confirm=auto_confirm)
            self._upsert_workflow(workflow_id, workflow, "PUT")

    def delete_workflow(self, workflow_id: str) -> None:
        raise NotImplementedError()

    def submit_workflow(
        self,
        workflow_id: str,
        request: Optional[WorkflowSubmitRequest] = None,
        auto_confirm: bool = False,
    ) -> WorkflowSubmitResult:
        """Submits a workflow for processing.

        Returns a WorkflowSubmitResult which contains the run ID.
        """
        self._confirm("Submit", auto_confirm=auto_confirm)

        request = request or WorkflowSubmitRequest()

        workflow: Optional[Workflow] = map_opt(
            lambda r: r.workflow, self.get_workflow(workflow_id)
        )

        if not workflow:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found.")

        workflow_def = workflow.definition

        request = request.copy()

        # Ensure arguments
        request.args = self.settings.add_default_args(
            workflow_definition=workflow_def, args=request.args
        )
        request.ensure_args_match(workflow_def)

        logger.debug("Submitting workflow...")
        start = perf_counter()
        resp = self._call_api(
            "POST",
            SUBMIT_WORKFLOW_ROUTE.format(workflow_id=workflow_id),
            data=request.json(),
        )
        result = WorkflowSubmitResult(**resp)
        end = perf_counter()
        logger.debug(f"Submit took {end - start:.2f} seconds.")
        logger.debug(result.json(indent=2))

        return result

    def upsert_and_submit_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        request: Optional[WorkflowSubmitRequest] = None,
        workflow_id: Optional[str] = None,
        auto_confirm: bool = False,
    ) -> WorkflowSubmitResult:
        if workflow_id is None:
            if not workflow_definition.workflow_id:
                raise NoWorkflowIDError(
                    "If no workflow ID is specified, "
                    "the workflow definition must have a "
                    "workflow_id field set"
                )
            workflow_id = workflow_definition.workflow_id
        self.upsert_workflow(workflow_definition, workflow_id)
        return self.submit_workflow(workflow_id, request, auto_confirm=auto_confirm)

    def list_workflow_runs(
        self,
        workflow_id: str,
        page_limit: Optional[int] = None,
        page_token: Optional[str] = None,
        max_pages: Optional[int] = None,
        sort_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> Iterable[WorkflowRunRecord]:
        route = LIST_WORKFLOW_RUNS_ROUTE.format(workflow_id=workflow_id)
        yield from self._yield_page_results(
            route,
            WorkflowRunRecordListResponse,
            page_limit=page_limit,
            page_token=page_token,
            max_pages=max_pages,
            sort_by=sort_by,
            descending=descending,
        )

    def _upsert_workflow(self, workflow_id: str, workflow: Workflow, verb: str) -> None:
        if verb not in ("PUT", "POST"):
            raise ValueError(f"Invalid verb: {verb}. Must be PUT or POST.")
        logger.debug("Uploading code...")
        start = perf_counter()
        self._upload_code(workflow.definition)
        end = perf_counter()
        logger.debug(f"Uploading code took {end - start:.2f} seconds.")

        self._call_api(
            verb, WORKFLOW_ROUTE.format(workflow_id=workflow_id), data=workflow.json()
        )

    # ## RUNS ##

    def get_workflow_run(
        self, run_id: str, dataset_id: Optional[str] = None
    ) -> Optional[WorkflowRunRecord]:
        route = FETCH_WORKFLOW_RUN_ROUTE.format(run_id=run_id)
        if dataset_id:
            route += f"?dataset={dataset_id}"
        try:
            result = self._call_api("GET", route)
            return WorkflowRunRecordResponse.parse_obj(result).record
        except HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_workflow_log(self, run_id: str) -> Optional[str]:
        route = FETCH_WORKFLOW_RUN_LOG_ROUTE.format(run_id=run_id)
        try:
            result = self._call_api_text("GET", route)
            return result
        except HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def list_job_partition_runs(
        self,
        run_id: str,
        job_id: str,
        page_limit: Optional[int] = None,
        page_token: Optional[str] = None,
        max_pages: Optional[int] = None,
        sort_by: Optional[str] = None,
        descending: Optional[bool] = None,
    ) -> Iterable[JobPartitionRunRecord]:
        route = LIST_JOB_PARTITION_RUNS_ROUTE.format(run_id=run_id, job_id=job_id)
        yield from self._yield_page_results(
            route,
            JobPartitionRunRecordListResponse,
            page_limit=page_limit,
            page_token=page_token,
            max_pages=max_pages,
            sort_by=sort_by,
            descending=descending,
        )

    def get_job_partition_run(
        self, run_id: str, job_id: str, partition_id: str
    ) -> Optional[JobPartitionRunRecord]:
        route = FETCH_JOB_PARTITION_RUN_ROUTE.format(
            run_id=run_id, job_id=job_id, partition_id=partition_id
        )
        try:
            result = self._call_api("GET", route)
            return JobPartitionRunRecordResponse.parse_obj(result).record
        except HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_task_log(
        self, run_id: str, job_id: str, partition_id: str, task_id: str
    ) -> Optional[str]:
        route = FETCH_TASK_RUN_LOG_ROUTE.format(
            run_id=run_id, job_id=job_id, partition_id=partition_id, task_id=task_id
        )
        try:
            result = self._call_api_text("GET", route)
            return result
        except HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
