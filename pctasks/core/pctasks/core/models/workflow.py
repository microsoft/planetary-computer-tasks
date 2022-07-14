from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from pydantic import Field, validator

from pctasks.core.constants import WORKFLOW_SCHEMA_VERSION, WORKFLOW_SUBMIT_MESSAGE_TYPE
from pctasks.core.models.base import ForeachConfig, PCBaseModel, RunRecordId
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.event import CloudEvent, ItemNotificationConfig
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils import StrEnum
from pctasks.core.utils.template import DictTemplater


class BlobCreatedTriggerConfig(PCBaseModel):
    storage_account: str
    container: str
    matches: Optional[str]
    extensions: Optional[List[str]]


class BlobDeletedTriggerConfig(PCBaseModel):
    storage_account: str
    container: str
    matches: Optional[str]
    extensions: Optional[List[str]]


class TriggerConfig(PCBaseModel):
    blob_created: Optional[BlobCreatedTriggerConfig]
    blob_deleted: Optional[BlobDeletedTriggerConfig]


class JobConfig(PCBaseModel):
    id: Optional[str] = None
    tasks: List[TaskConfig]

    foreach: Optional[ForeachConfig] = None

    # Can move to a "Union" if more notifications are supported
    notifications: Optional[List[ItemNotificationConfig]] = None

    needs: Optional[Union[str, List[str]]] = None

    @validator("id")
    def _validate_jobs(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cls.validate_job_id(v)
        return v

    @classmethod
    def validate_job_id(cls, job_id: str) -> None:
        try:
            validate_table_key(job_id)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid job id '{job_id}': {e.INFO_MESSAGE}")

        if "," in job_id:
            raise ValueError(f"Invalid job id '{job_id}': cannot contain commas.")

    def get_id(self) -> str:
        """Gets the Job ID.

        Raises if no job ID is set, which should be set by either
        the workflow config logic or by the user.
        """
        if self.id is None:
            raise ValueError("Job ID not set.")
        return self.id

    def get_dependencies(self) -> Optional[List[str]]:
        """Returns a list of job IDs that this job is dependent on."""
        if not self.needs:
            return None
        if isinstance(self.needs, str):
            return [self.needs]
        return self.needs


class WorkflowConfig(PCBaseModel):
    name: str
    dataset: Union[DatasetIdentifier, str]
    group_id: Optional[str] = None
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    target_environment: Optional[str] = None
    args: Optional[List[str]] = None
    jobs: Dict[str, JobConfig]
    on: Optional[TriggerConfig] = None

    schema_version: str = Field(default=WORKFLOW_SCHEMA_VERSION, const=True)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        for id, job in self.jobs.items():
            if not job.id:
                job.id = id

    @validator("jobs")
    def _validate_jobs(cls, v: Dict[str, JobConfig]) -> Dict[str, JobConfig]:
        for job_id in v:
            # Only validate if job_id is set to None
            # Otherwise job validator will catch the error
            if not v[job_id].id:
                JobConfig.validate_job_id(job_id)
        return v

    @validator("dataset")
    def _validate_dataset(cls, v: Any) -> DatasetIdentifier:
        if isinstance(v, str):
            return DatasetIdentifier.from_string(v)
        return v

    def get_dataset_id(self) -> DatasetIdentifier:
        if isinstance(self.dataset, str):
            return DatasetIdentifier.from_string(self.dataset)
        return self.dataset

    def template_args(self, args: Optional[Dict[str, Any]]) -> "WorkflowConfig":
        return DictTemplater({"args": args}, strict=False).template_model(self)

    def get_argument_errors(
        self, args: Optional[Dict[str, Any]]
    ) -> Optional[List[str]]:
        """Checks if there are errors with provided arguments.

        Returns a list of error messages or None if there no errors.
        """
        args_keys: Set[str] = set(args.keys() if args else [])
        workflow_args: Set[str] = set(self.args or [])

        missing_args = workflow_args - args_keys
        unexpected_args = args_keys - workflow_args

        errors: List[str] = []
        if missing_args:
            errors.append(f"Args expected and not provided: {','.join(missing_args)}")
        if unexpected_args:
            errors.append(f"Unexpected args provided: {','.join(unexpected_args)}")

        if errors:
            return errors
        else:
            return None


class WorkflowSubmitMessage(PCBaseModel):
    workflow: WorkflowConfig
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    trigger_event: Optional[CloudEvent] = None
    type: str = Field(default=WORKFLOW_SUBMIT_MESSAGE_TYPE, const=True)
    args: Optional[Dict[str, Any]] = None

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(run_id=self.run_id, dataset_id=str(self.workflow.dataset))

    def get_workflow_with_templated_args(self) -> WorkflowConfig:
        if self.args is None:
            return self.workflow
        return self.workflow.template_args(self.args)

    @validator("args", always=True)
    def _validate_args(
        cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check that args match the workflow args."""
        if "workflow" not in values:
            raise ValueError("'workflow' is a required field.")
        errors = values["workflow"].get_argument_errors(v)

        if errors:
            raise ValueError(f"Argument errors: {';'.join(errors)}")

        return v


class WorkflowRunStatus(StrEnum):

    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowSubmitResult(PCBaseModel):
    """
    Result of submitting a workflow.
    Returned from the API, consumed by the submit client.
    """

    dataset: DatasetIdentifier
    run_id: str
    status: WorkflowRunStatus
    errors: Optional[List[str]] = None
