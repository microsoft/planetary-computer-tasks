from typing import Any, Dict, List, Optional, Set, Union

from pydantic import Field, validator

from pctasks.core.constants import WORKFLOW_SCHEMA_VERSION
from pctasks.core.models.base import ForeachConfig, PCBaseModel
from pctasks.core.models.event import CloudEvent, ItemNotificationConfig
from pctasks.core.models.record import Record
from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils import StrEnum
from pctasks.core.utils.template import DictTemplater


class WorkflowRecordType(StrEnum):
    WORKFLOW = "Workflow"


class WorkflowArgumentError(Exception):
    def __init__(self, message: str, errors: List[str]):
        self.errors = errors
        super().__init__(message)


class StorageTriggerDefinition(PCBaseModel):
    storage_account: str
    container: str
    matches: Optional[str]
    extensions: Optional[List[str]]
    aoi: Optional[Dict[str, Any]]


class TriggerDefinition(PCBaseModel):
    storage_event: Optional[StorageTriggerDefinition]
    schedule: Optional[str]


class JobDefinition(PCBaseModel):
    id: Optional[str] = None
    tasks: List[TaskDefinition]

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


class WorkflowDefinition(PCBaseModel):
    """

    is_streaming: bool, default False
        Indicates whether this workflow is a batch (the default) or streaming
        workflow. Streaming workflows have special requirements, and behave a
        bit differently on the backend.
    """

    workflow_id: Optional[str] = Field(default=None, alias="id")
    name: str
    dataset_id: str = Field(alias="dataset")
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    target_environment: Optional[str] = None
    args: Optional[List[str]] = None
    jobs: Dict[str, JobDefinition]
    on: Optional[TriggerDefinition] = None
    is_streaming: bool = False

    schema_version: str = Field(default=WORKFLOW_SCHEMA_VERSION, const=True)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        for id, job in self.jobs.items():
            if not job.id:
                job.id = id

    @validator("jobs")
    def _validate_jobs(cls, v: Dict[str, JobDefinition]) -> Dict[str, JobDefinition]:
        for job_id in v:
            # Only validate if job_id is set to None
            # Otherwise job validator will catch the error
            if not v[job_id].id:
                JobDefinition.validate_job_id(job_id)
        return v

    @validator("is_streaming")
    def _validate_is_streaming(
        cls, v: bool, values: Dict[str, Any], **kwargs: Dict[str, Any]
    ) -> bool:
        """
        A streaming workflow is similar to other pctasks workflows, but requires a few
        additional properties on the streaming tasks within the workflow:

        1. The task must define the streaming-related properties using `args`:

        - `queue_url`
        - `visibility_timeout`
        - `min_replica_count`
        - `max_replica_count`
        - `polling_interval`
        - `trigger_queue_length`

        2. The workflow should set the top-level `is_streaming` property to `true`.

        In addition to these schema-level requirements, there are some expectations in
        how the workflow behaves at runtime. In general, streaming tasks should expect
        to run indefinitely. They should continuously process messages from a queue,
        and leave starting, stopping, and scaling to the pctasks framework.
        """
        if v:
            jobs = values["jobs"]
            n_jobs = len(jobs)
            if n_jobs != 1:
                raise ValueError(
                    f"Streaming workflows must have exactly one job. Got "
                    f"{n_jobs} instead."
                )
            job = list(jobs.values())[0]

            n_tasks = len(job.tasks)
            if n_tasks != 1:
                raise ValueError(
                    f"Streaming workflows must have exactly one task. Got "
                    f"{n_tasks} instead."
                )

            task = job.tasks[0]

            try:
                streaming_options = task.args["streaming_options"]
            except KeyError as e:
                raise ValueError("Streaming workflow must define 'streaming_options'") from e

            for key in [
                "queue_url",
                "visibility_timeout",
                "min_replica_count",
                "max_replica_count",
                "polling_interval",
                "trigger_queue_length",
            ]:
                if key not in streaming_options:
                    raise ValueError(
                        f"Streaming workflows must define the '{key}' property "
                        f"on the task."
                    )

        return v

    def template_args(self, args: Optional[Dict[str, Any]]) -> "WorkflowDefinition":
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


class Workflow(PCBaseModel):
    id: str
    definition: WorkflowDefinition

    @property
    def dataset_id(self) -> str:
        return self.definition.dataset_id

    @classmethod
    def from_definition(
        cls, definition: WorkflowDefinition, id: Optional[str] = None
    ) -> "Workflow":
        id = id or definition.workflow_id
        if not id:
            raise ValueError(
                "Workflow ID not set in definition and none supplied as an argument."
            )

        return cls(id=id, definition=definition)


class WorkflowRecord(Record):
    type: str = Field(default=WorkflowRecordType.WORKFLOW, const=True)
    workflow_id: str
    workflow: Workflow

    log_uri: Optional[str] = None

    # Status -> count
    workflow_run_counts: Dict[str, int] = Field(default_factory=dict)

    def get_id(self) -> str:
        return self.workflow_id

    @classmethod
    def from_workflow(cls, workflow: Workflow) -> "WorkflowRecord":
        return cls(workflow_id=workflow.id, workflow=workflow)


class WorkflowSubmitMessage(PCBaseModel):
    run_id: str
    workflow: Workflow
    trigger_event: Optional[CloudEvent] = None
    args: Optional[Dict[str, Any]] = None

    def get_workflow_with_templated_args(self) -> Workflow:
        if self.args is None:
            return self.workflow
        return self.workflow.copy(
            update={"definition": self.workflow.definition.template_args(self.args)}
        )

    def ensure_args_match(self) -> None:
        """Raise exception if args don't match the workflow args."""
        errors = self.workflow.definition.get_argument_errors(self.args)

        if errors:
            raise WorkflowArgumentError(f"Argument errors: {';'.join(errors)}", errors)


class WorkflowSubmitRequest(PCBaseModel):
    trigger_event: Optional[CloudEvent] = None
    args: Optional[Dict[str, Any]] = None

    def ensure_args_match(self, workflow_definition: WorkflowDefinition) -> None:
        """Raise exception if args don't match the workflow args."""
        errors = workflow_definition.get_argument_errors(self.args)

        if errors:
            raise WorkflowArgumentError(f"Argument errors: {';'.join(errors)}", errors)


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

    run_id: str
    status: WorkflowRunStatus
    errors: Optional[List[str]] = None
