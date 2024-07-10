import logging
import math
import random
import time
from concurrent import futures
from typing import Any, Dict, Iterable, List, Optional, Union

from azure.storage.queue import BinaryBase64DecodePolicy, BinaryBase64EncodePolicy
from opencensus.ext.azure.log_exporter import AzureLogHandler

from pctasks.core.cosmos.container import CosmosDBContainer
from pctasks.core.cosmos.containers.workflow_runs import WorkflowRunsContainer
from pctasks.core.logging import StorageLogger
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.core.models.run import (
    JobPartitionRunRecord,
    JobPartitionRunStatus,
    JobRunStatus,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import CompletedTaskResult, FailedTaskResult
from pctasks.core.models.workflow import JobDefinition, WorkflowSubmitMessage
from pctasks.core.queues import QueueService
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.utils import StrEnum, grouped, map_opt
from pctasks.run.constants import TASKS_TEMPLATE_PATH
from pctasks.run.dag import sort_jobs
from pctasks.run.errors import WorkflowRunRecordError
from pctasks.run.models import (
    FailedTaskSubmitResult,
    JobPartition,
    JobPartitionSubmitMessage,
    PreparedTaskData,
    SuccessfulTaskSubmitResult,
)
from pctasks.run.settings import WorkflowExecutorConfig
from pctasks.run.task import get_task_runner
from pctasks.run.task.prepare import prepare_task_data
from pctasks.run.template import (
    template_foreach,
    template_job_with_item,
    template_notification,
)
from pctasks.run.utils import get_workflow_log_path
from pctasks.run.workflow.executor.models import (
    JobPartitionState,
    JobPartitionStateStatus,
    TaskState,
    TaskStateStatus,
)

logger = logging.getLogger(__name__)
azlogger = logging.getLogger("monitor.pctasks.run.workflow.executor.remote")
azhandler = None  # initialized later in `_init_azlogger`


class EventTypes(StrEnum):
    workflow_run_created = "WorkflowRunCreated"
    workflow_run_finished = "WorkflowRunFinished"
    job_created = "JobCreated"
    job_finished = "JobFinished"
    job_partition_created = "JobPartitionCreated"
    job_partition_finished = "JobPartitionFinished"
    task_created = "TaskCreated"
    task_finished = "TaskFinished"


class RecordLevels(StrEnum):
    workflow_run = "WorkflowRun"
    job = "Job"
    job_partition = "JobPartition"
    task = "Task"


def _init_azlogger() -> None:
    # AzureLogHandler is slow to initialize
    # do it once here
    global azhandler

    if azhandler is None:
        logger.debug("Initializing AzureLogHandler")
        azlogger.setLevel(logging.INFO)
        try:
            azhandler = AzureLogHandler()
        except ValueError:
            # missing instrumentation key
            azhandler = False
            logger.warning("Unable to initialize AzureLogHandler")
        else:
            azhandler.setLevel(logging.INFO)
            azlogger.addHandler(azhandler)


class RemoteWorkflowRunnerError(Exception):
    pass


class WorkflowFailedError(Exception):
    pass


def update_workflow_run_status(
    container: CosmosDBContainer[WorkflowRunRecord],
    workflow_run: WorkflowRunRecord,
    status: WorkflowRunStatus,
    log_uri: Optional[str] = None,
) -> None:
    record = container.get(workflow_run.run_id, partition_key=workflow_run.run_id)
    if not record:
        raise WorkflowRunRecordError(
            f"Workflow run record not found: {workflow_run.run_id}"
        )

    update = False
    if record.status != status:
        record.set_status(status)
        update = True
    if log_uri:
        record.log_uri = log_uri
        update = True

    if update:
        container.put(record)

    if status in (WorkflowRunStatus.FAILED, WorkflowRunStatus.COMPLETED):
        event_type = EventTypes.workflow_run_finished
        message = "Workflow Run finished"
    else:
        event_type = EventTypes.workflow_run_created
        message = "Workflow Run created"

    custom_dimensions = {
        "workflowId": workflow_run.workflow_id,
        "datasetId": workflow_run.dataset_id,
        "runId": workflow_run.run_id,
        "status": status.value,
        "recordLevel": RecordLevels.workflow_run,
        "type": event_type,
    }

    level = logging.WARNING if status == WorkflowRunStatus.FAILED else logging.INFO
    azlogger.log(
        level,
        message,
        extra={"custom_dimensions": custom_dimensions},
    )


def update_job_run_status(
    container: CosmosDBContainer[WorkflowRunRecord],
    workflow_run: WorkflowRunRecord,
    job_id: str,
    status: JobRunStatus,
    errors: Optional[List[str]] = None,
) -> None:
    record = container.get(workflow_run.run_id, partition_key=workflow_run.run_id)
    if not record:
        raise WorkflowRunRecordError(
            f"Workflow run record not found: {workflow_run.run_id}"
        )
    job_run = record.get_job_run(job_id)
    if not job_run:
        raise WorkflowRunRecordError(
            f"Job run not found: {workflow_run.run_id} {job_id}"
        )
    if job_run.status != status:
        job_run.set_status(status)
        if errors:
            job_run.add_errors(errors)

        if status == JobRunStatus.FAILED:
            # If this is marking the job as failed,
            # mark all pending jobs as cancelled.
            for job in record.jobs:
                if job.status == JobRunStatus.PENDING:
                    job.set_status(JobRunStatus.CANCELLED)

            # Also mark the workflow as failed.
            record.set_status(WorkflowRunStatus.FAILED)

        container.put(record)

    if status in (
        JobRunStatus.FAILED,
        JobRunStatus.COMPLETED,
        JobRunStatus.CANCELLED,
        JobRunStatus.SKIPPED,
    ):
        event_type = EventTypes.job_finished
        message = "Job finished"
    else:
        event_type = EventTypes.job_created
        message = "Job created"

    custom_dimensions = {
        "workflowId": workflow_run.workflow_id,
        "datasetId": workflow_run.dataset_id,
        "runId": workflow_run.run_id,
        "jobId": job_id,
        "status": status.value,
        "recordLevel": RecordLevels.job,
        "type": event_type,
        "errors": errors,
    }

    level = logging.WARNING if status == JobRunStatus.FAILED else logging.INFO
    azlogger.log(
        level,
        message,
        extra={"custom_dimensions": custom_dimensions},
    )


def update_job_partition_run_status(
    container: CosmosDBContainer[JobPartitionRunRecord],
    run_id: str,
    job_partition_run_id: str,
    status: JobPartitionRunStatus,
    workflow_id: str,
    dataset_id: str,
    job_id: str,
    partition_id: str,
) -> None:
    record = container.get(job_partition_run_id, partition_key=run_id)
    if not record:
        raise WorkflowRunRecordError(
            f"Job Partition run record not found: {job_partition_run_id}"
        )
    if record.status != status:
        record.set_status(status)
        container.put(record)

    if status in (
        JobPartitionRunStatus.FAILED,
        JobPartitionRunStatus.COMPLETED,
    ):
        event_type = EventTypes.job_partition_finished
        message = "Job partition finished"
    else:
        event_type = EventTypes.job_partition_created
        message = "Job partition created"

    custom_dimensions = {
        "workflowId": workflow_id,
        "datasetId": dataset_id,
        "runId": run_id,
        "jobId": job_id,
        "partitionId": partition_id,
        "status": status.value,
        "recordLevel": RecordLevels.job_partition,
        "type": event_type,
    }

    level = logging.WARNING if status == JobPartitionRunStatus.FAILED else logging.INFO
    azlogger.log(
        level,
        message,
        extra={"custom_dimensions": custom_dimensions},
    )


def update_task_run_status(
    container: CosmosDBContainer[JobPartitionRunRecord],
    run_id: str,
    job_partition_run_id: str,
    task_id: str,
    status: TaskRunStatus,
    errors: Optional[List[str]] = None,
    log_uri: Optional[str] = None,
    workflow_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    job_id: Optional[str] = None,
    partition_id: Optional[str] = None,
) -> None:
    record = container.get(job_partition_run_id, partition_key=run_id)
    if not record:
        raise WorkflowRunRecordError(
            f"Job Partition run record not found: {job_partition_run_id}"
        )

    task_run = record.get_task(task_id)
    if not task_run:
        raise WorkflowRunRecordError(
            f"Task run not found: {job_partition_run_id} {task_id}"
        )
    if task_run.status != status:
        task_run.set_status(status)
        if errors:
            task_run.add_errors(errors)
        if log_uri:
            task_run.log_uri = log_uri

        if status in [TaskRunStatus.FAILED, TaskRunStatus.CANCELLED]:
            # If this is marking the task as failed or cancelled,
            # mark all pending tasks as cancelled.
            for task in record.tasks:
                if task.status == TaskRunStatus.PENDING:
                    task.set_status(TaskRunStatus.CANCELLED)

            # Also mark the job partition as failed.
            record.set_status(JobPartitionRunStatus.FAILED)

        container.put(record)

    if status in (TaskRunStatus.RECEIVED, TaskRunStatus.SUBMITTING):
        # We only want to log task creation once
        return None
    elif status in (
        TaskRunStatus.FAILED,
        TaskRunStatus.COMPLETED,
        TaskRunStatus.CANCELLED,
    ):
        event_type = EventTypes.task_finished
        message = "Task finished"
    else:
        event_type = EventTypes.task_created
        message = "Task created"

    custom_dimensions = {
        "workflowId": workflow_id,
        "datasetId": dataset_id,
        "runId": run_id,
        "jobId": job_id,
        "partitionId": partition_id,
        "taskId": task_id,
        "status": status.value,
        "recordLevel": RecordLevels.task,
        "type": event_type,
        "errors": errors,
    }

    level = logging.WARNING if status == TaskRunStatus.FAILED else logging.INFO
    azlogger.log(
        level,
        message,
        extra={"custom_dimensions": custom_dimensions},
    )


class RemoteWorkflowExecutor:
    """Executes a workflow through submitting tasks remotely via a task runner."""

    def __init__(self, settings: Optional[WorkflowExecutorConfig] = None) -> None:
        self.config = settings or WorkflowExecutorConfig.get()
        self.task_runner = get_task_runner(self.config.run_settings)

    def __enter__(self) -> "RemoteWorkflowExecutor":
        self.task_runner.__enter__()
        _init_azlogger()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.task_runner.__exit__(exc_type, exc_value, traceback)

    def create_job_partition_states(
        self,
        submit_msgs: Iterable[JobPartitionSubmitMessage],
        container: CosmosDBContainer[JobPartitionRunRecord],
        workflow_id: str,
    ) -> List[JobPartitionState]:
        records: List[JobPartitionRunRecord] = []
        states: List[JobPartitionState] = []

        for submit_msg in submit_msgs:
            job_partition_run = JobPartitionRunRecord.from_definition(
                submit_msg.job_partition.partition_id,
                submit_msg.job_partition.definition,
                submit_msg.run_id,
                status=JobPartitionRunStatus.RUNNING,
            )
            job_partition_state = JobPartitionState.create(
                submit_msg,
                job_part_run_record_id=job_partition_run.get_id(),
                settings=self.config.run_settings,
            )

            if job_partition_state.current_task:
                task_state = job_partition_state.current_task
                task_run = job_partition_run.get_task(task_state.task_id)
                if not task_run:
                    job_partition_run.status = JobPartitionRunStatus.FAILED
                    raise WorkflowRunRecordError(
                        f"Task {task_state.task_id} not found in "
                        f"job partition {job_partition_run.get_id()}"
                    )

                task_run.status = TaskRunStatus.SUBMITTING
            else:
                job_partition_run.set_status(JobPartitionRunStatus.FAILED)
                job_partition_state.status = JobPartitionStateStatus.NOTASKS

            records.append(job_partition_run)
            states.append(job_partition_state)

        # Bulk insert job partition run records
        container.bulk_put(records)

        return states

    def send_notification(
        self, notification_submit_message: NotificationSubmitMessage
    ) -> None:
        """Send a notification to the notification queue."""
        queue_settings = self.config.run_settings.notification_queue
        with QueueService.from_connection_string(
            connection_string=queue_settings.connection_string,
            queue_name=queue_settings.queue_name,
            message_encode_policy=BinaryBase64EncodePolicy(),
            message_decode_policy=BinaryBase64DecodePolicy(),
        ) as queue:
            msg_id = queue.send_message(notification_submit_message.dict())
            logger.info(f"  - Notification sent, queue id {msg_id}")

    def handle_job_part_notifications(self, job_state: JobPartitionState) -> None:
        # TODO: Handle job notifications

        job_submit_msg = job_state.job_part_submit_msg
        job_config = job_submit_msg.job_partition
        if job_config.definition.notifications:
            for notification in job_config.definition.notifications:
                templated_notification = template_notification(
                    notification=notification,
                    task_outputs=job_state.task_outputs,
                )
                notification_message = templated_notification.to_message()
                notification_submit_msg = NotificationSubmitMessage(
                    notification=notification_message,
                    target_environment=job_submit_msg.target_environment,
                    processing_id=job_state.job_part_submit_msg.get_run_record_id(),
                )

                self.send_notification(notification_submit_msg)

    def cancel_tasks(self, job_part_state: JobPartitionState) -> None:
        # Called when a job partition is cancelled, prior to submitting tasks.
        task_state = job_part_state.current_task
        if task_state:
            task_state.change_status(TaskStateStatus.CANCELLED)
            container = WorkflowRunsContainer(
                JobPartitionRunRecord, db=self.config.get_cosmosdb()
            )
            job_part_run = container.get(
                job_part_state.job_part_run_record_id,
                partition_key=job_part_state.run_id,
            )
            if job_part_run:
                for task in job_part_run.tasks:
                    if task.status in [TaskRunStatus.PENDING, TaskRunStatus.SUBMITTING]:
                        task.set_status(TaskRunStatus.CANCELLED)
                container.put(job_part_run)

    def update_submit_result(
        self,
        task_state: TaskState,
        submit_result: Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult],
        container: CosmosDBContainer[JobPartitionRunRecord],
        run_id: str,
        job_partition_run_id: str,
        workflow_id: str,
        dataset_id: str,
        job_id: str,
        partition_id: str,
    ) -> TaskRunStatus:
        """Updates a task state and task run status based on the submit result.

        Returns the resulting task run status.
        """
        task_state.set_submitted(submit_result)

        if isinstance(submit_result, FailedTaskSubmitResult):
            update_task_run_status(
                container,
                run_id=run_id,
                job_partition_run_id=job_partition_run_id,
                task_id=task_state.task_id,
                status=TaskRunStatus.FAILED,
                errors=["Task failed to submit."] + submit_result.errors,
                workflow_id=workflow_id,
                dataset_id=dataset_id,
                job_id=job_id,
                partition_id=partition_id,
            )
            return TaskRunStatus.FAILED
        else:
            update_task_run_status(
                container,
                run_id=run_id,
                job_partition_run_id=job_partition_run_id,
                task_id=task_state.task_id,
                status=TaskRunStatus.SUBMITTED,
                workflow_id=workflow_id,
                dataset_id=dataset_id,
                job_id=job_id,
                partition_id=partition_id,
            )
            return TaskRunStatus.SUBMITTED

    def complete_job_partition_group(
        self,
        run_id: str,
        job_id: str,
        group_id: str,
        job_part_states: List[JobPartitionState],
        container: CosmosDBContainer[JobPartitionRunRecord],
        max_concurrent_partition_tasks: int,
        is_last_job: bool,
        task_io_storage: BlobStorage,
        task_log_storage: BlobStorage,
        workflow_id: str,
        dataset_id: str,
    ) -> List[Dict[str, Any]]:
        """Complete job partitions and return the results.

        This is a blocking loop that is meant to be called on it's own thread.
        """
        completed_job_count = 0
        running_task_count = 0
        failed_job_count = 0
        total_job_count = len(job_part_states)
        _jobs_left = (
            lambda: total_job_count - completed_job_count - failed_job_count
        )  # noqa: E731
        _report_status = lambda: logger.info(  # noqa: E731
            f"{job_id} {group_id} status: "
            f"{completed_job_count} completed, "
            f"{failed_job_count} failed, "
            f"{_jobs_left()} remaining, "
            f"{running_task_count} tasks running"
        )

        _last_runner_poll_time: float = time.monotonic()
        runner_failed_tasks: Dict[str, Dict[str, str]] = {}

        try:
            while _jobs_left() > 0:

                # Check the task runner for any failed tasks.
                if (
                    time.monotonic() - _last_runner_poll_time
                    > self.config.run_settings.task_poll_seconds
                ):
                    current_tasks = {
                        jps.partition_id: {
                            jps.current_task.task_id: jps.current_task.task_runner_id  # noqa: E501
                        }
                        for jps in job_part_states
                        if jps.current_task and jps.current_task.task_runner_id
                    }

                    runner_failed_tasks = self.task_runner.get_failed_tasks(
                        current_tasks
                    )
                    _last_runner_poll_time = time.monotonic()

                for job_part_state in job_part_states:
                    part_id = job_part_state.job_part_submit_msg.partition_id

                    # For each job partition in this group, process
                    # the status of the current task.

                    if job_part_state.current_task:
                        task_state = job_part_state.current_task
                        part_run_record_id = job_part_state.job_part_run_record_id

                        #
                        # Update task state
                        #

                        # Update task state if waiting and
                        # wait time expired, sets status to NEW
                        task_state.update_if_waiting()

                        if task_state.should_check_output(
                            self.config.run_settings.check_output_seconds
                        ):
                            task_state.process_output_if_available(
                                task_io_storage, self.config.run_settings
                            )

                        # If not completed through output,
                        # check the status blob
                        if task_state.should_check_status_blob(
                            self.config.run_settings.check_status_blob_seconds
                        ):
                            task_state.process_status_blob_if_available(task_io_storage)

                        if part_id in runner_failed_tasks:
                            if task_state.task_id in runner_failed_tasks[part_id]:
                                error_msg = runner_failed_tasks[part_id][
                                    task_state.task_id
                                ]
                                task_state.set_failed([error_msg])

                        #
                        # Act on task state
                        #

                        if task_state.status == TaskStateStatus.NEW:
                            # New task, submit it
                            # wait if max concurrent tasks are already running
                            if running_task_count >= max_concurrent_partition_tasks:
                                continue
                            else:
                                running_task_count += 1

                            update_task_run_status(
                                container,
                                run_id=run_id,
                                job_partition_run_id=part_run_record_id,
                                task_id=task_state.task_id,
                                status=TaskRunStatus.SUBMITTING,
                                workflow_id=workflow_id,
                                dataset_id=dataset_id,
                                job_id=job_id,
                                partition_id=job_part_state.partition_id,
                            )

                            job_part_state.current_task.submit(self.task_runner)
                            submit_result = job_part_state.current_task.submit_result
                            if not submit_result:
                                raise Exception(
                                    f"Unexpected submit result: {submit_result}"
                                )

                            self.update_submit_result(
                                task_state,
                                submit_result,
                                container,
                                run_id=run_id,
                                job_partition_run_id=part_run_record_id,
                                workflow_id=workflow_id,
                                dataset_id=dataset_id,
                                job_id=job_id,
                                partition_id=job_part_state.partition_id,
                            )

                        elif task_state.status == TaskStateStatus.SUBMITTED:
                            # Job is running...
                            pass

                        elif task_state.status == TaskStateStatus.RUNNING:
                            # Job is still running...
                            pass
                            if not task_state.status_updated:
                                update_task_run_status(
                                    container,
                                    run_id=run_id,
                                    job_partition_run_id=part_run_record_id,
                                    task_id=task_state.task_id,
                                    status=TaskRunStatus.RUNNING,
                                )
                                task_state.status_updated = True

                        elif task_state.status == TaskStateStatus.WAITING:
                            # If we just moved the job state to waiting,
                            # update the record.
                            running_task_count -= 1

                            if not task_state.status_updated:
                                update_task_run_status(
                                    container,
                                    run_id=run_id,
                                    job_partition_run_id=part_run_record_id,
                                    task_id=task_state.task_id,
                                    status=TaskRunStatus.WAITING,
                                )
                                task_state.status_updated = True

                        elif task_state.status == TaskStateStatus.FAILED:
                            running_task_count -= 1

                            logger.warning(
                                f"Task failed: {job_part_state.job_id} "
                                f"- {task_state.task_id}"
                            )
                            errors: Optional[List[str]] = None
                            task_result = task_state.task_result
                            if isinstance(task_result, FailedTaskResult):
                                errors = task_result.errors

                            for error in errors or []:
                                logger.warning(f"  - {error}")

                            failed_job_count += 1

                            job_part_state.status = JobPartitionStateStatus.FAILED
                            job_part_state.current_task = None

                            # Mark this task as failed (will also fail job part)

                            update_task_run_status(
                                container,
                                run_id=run_id,
                                job_partition_run_id=part_run_record_id,
                                task_id=task_state.task_id,
                                status=TaskRunStatus.FAILED,
                                errors=errors,
                                log_uri=task_state.get_log_uri(task_log_storage),
                            )

                            logger.warning(
                                "Job partition failed: "
                                f"{job_part_state.job_id}:{part_id}"
                            )

                            _report_status()

                        elif task_state.status == TaskStateStatus.COMPLETED:
                            running_task_count -= 1

                            logger.info(
                                f"Task completed: {job_part_state.job_id}:{part_id}"
                                f":{task_state.task_id}"
                            )
                            if not isinstance(
                                task_state.task_result, CompletedTaskResult
                            ):
                                task_state.set_failed(
                                    [
                                        "Unexpected task result: "
                                        f"{task_state.task_result} "
                                        f"of type {type(task_state.task_result)}"
                                    ]
                                )
                                continue

                            if (not is_last_job) or (job_part_state.has_next_task):
                                job_part_state.task_outputs[task_state.task_id] = {
                                    "output": task_state.task_result.output
                                }
                            else:
                                # Clear task output to save memory
                                task_state.task_result.output = {}

                            update_task_run_status(
                                container,
                                run_id=run_id,
                                job_partition_run_id=part_run_record_id,
                                task_id=task_state.task_id,
                                status=TaskRunStatus.COMPLETED,
                                log_uri=task_state.get_log_uri(task_log_storage),
                            )

                            try:
                                job_part_state.prepare_next_task(
                                    self.config.run_settings
                                )
                            except Exception as e:
                                logger.exception(e)
                                job_part_state.status = JobPartitionStateStatus.FAILED
                                failed_job_count += 1
                                update_job_partition_run_status(
                                    container,
                                    run_id=run_id,
                                    job_partition_run_id=part_run_record_id,
                                    status=JobPartitionRunStatus.FAILED,
                                    workflow_id=workflow_id,
                                    dataset_id=dataset_id,
                                    job_id=job_id,
                                    partition_id=part_id,
                                )

                            # Handle job completion
                            if (
                                job_part_state.current_task is None
                                and job_part_state.status
                                != JobPartitionStateStatus.FAILED
                            ):
                                try:
                                    job_part_state.status = (
                                        JobPartitionStateStatus.SUCCEEDED
                                    )
                                    update_job_partition_run_status(
                                        container,
                                        run_id=run_id,
                                        job_partition_run_id=part_run_record_id,
                                        status=JobPartitionRunStatus.COMPLETED,
                                        workflow_id=workflow_id,
                                        dataset_id=dataset_id,
                                        job_id=job_id,
                                        partition_id=part_id,
                                    )
                                    self.handle_job_part_notifications(job_part_state)

                                    # If this is the last job, clear the task output
                                    # to save memory
                                    if is_last_job:
                                        job_part_state.task_outputs = {}

                                except Exception:
                                    job_part_state.status = (
                                        JobPartitionStateStatus.FAILED
                                    )
                                    failed_job_count += 1
                                    update_job_partition_run_status(
                                        container,
                                        run_id=run_id,
                                        job_partition_run_id=part_run_record_id,
                                        status=JobPartitionRunStatus.FAILED,
                                        workflow_id=workflow_id,
                                        dataset_id=dataset_id,
                                        job_id=job_id,
                                        partition_id=part_id,
                                    )
                                completed_job_count += 1
                                logger.info(
                                    f"Job partition completed: {job_id}:{part_id}"
                                )

                            _report_status()

                time.sleep(0.25 + ((random.randint(0, 10) / 100) - 0.05))

            logger.info(f"Partition group {group_id} completed!")

        except Exception as e:
            logger.exception(e)
            raise

        return [job_state.task_outputs for job_state in job_part_states]

    def execute_job_partitions(
        self,
        run_id: str,
        job_id: str,
        workflow_run: WorkflowRunRecord,
        job_def: JobDefinition,
        total_job_part_count: int,
        task_data: List[PreparedTaskData],
        is_last_job: bool,
        job_part_states: List[JobPartitionState],
        wf_run_container: CosmosDBContainer[WorkflowRunRecord],
        jp_container: CosmosDBContainer[JobPartitionRunRecord],
        pool: futures.ThreadPoolExecutor,
        task_io_storage: BlobStorage,
        task_log_storage: BlobStorage,
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Execute job partitions and return the results.

        If return value is None, then the workflow is failed.
        The output will be an empty dict if the job is the last job in the workflow.
        Otherwise it will be the output of the job partitions.
        """

        try:
            # Split the job partitions into groups
            # based on the number of threads.
            # Each thread will execute and monitor
            # a group of job partitions.
            grouped_job_partition_states = [
                (list(g), group_num)
                for group_num, g in enumerate(
                    grouped(
                        job_part_states,
                        int(
                            math.ceil(
                                len(job_part_states)
                                / self.config.run_settings.remote_runner_threads
                            )
                        ),
                    )
                )
            ]

            logger.info("Executing job partitions...")

            job_part_futures = {
                pool.submit(
                    self.complete_job_partition_group,
                    run_id,
                    job_id,
                    f"job-part-group-{group_num}",
                    job_state_group,
                    jp_container,
                    int(
                        math.ceil(
                            self.config.run_settings.max_concurrent_workflow_tasks
                            / self.config.run_settings.remote_runner_threads
                        )
                    ),
                    is_last_job,
                    task_io_storage=task_io_storage,
                    task_log_storage=task_log_storage,
                    workflow_id=workflow_run.workflow_id,
                    dataset_id=workflow_run.dataset_id,
                ): job_state_group
                for (
                    job_state_group,
                    group_num,
                ) in grouped_job_partition_states
            }

            job_results: List[Dict[str, Any]] = []

            job_done_count = 0
            failed_job_part_errors: List[str] = []
            job_failed = False
            for job_future in futures.as_completed(job_part_futures.keys()):
                job_part_states = job_part_futures[job_future]

                if job_future.cancelled():
                    job_failed = True
                    failed_job_part_errors.append(
                        "Job partitions failed due to thread cancellation."
                    )

                future_error = job_future.exception()
                if future_error:
                    job_failed = True
                    failed_job_part_errors.append(
                        f"Job partitions thread failed with {future_error}"
                    )

                job_done_count += len(job_part_states)

                for job_part_state in job_part_states:
                    if job_part_state.status == JobPartitionStateStatus.FAILED:
                        job_failed = True
                        logger.warning(
                            f"JOB PART FAILED: {job_id} "
                            f"{job_part_state.partition_id}"
                        )
                    else:
                        if not is_last_job:
                            # If this is not the last job in the
                            # workflow, record job outputs so they
                            # can be used to template downstream jobs.
                            # If this is the last job in the workflow,
                            # don't collect any job results.
                            job_results.append(job_part_state.task_outputs)

                logger.info(
                    f"Job {job_id} partition progress: "
                    f"({job_done_count}/{total_job_part_count})"
                )

            # ## PROCESS JOB PARTITION RESULTS

            if job_failed:
                update_job_run_status(
                    wf_run_container,
                    workflow_run,
                    job_def.get_id(),
                    JobRunStatus.FAILED,
                    errors=failed_job_part_errors,
                )
                return None
            else:
                result: Union[Dict[str, Any], List[Dict[str, Any]]]

                if is_last_job:
                    result = {}
                elif len(job_results) == 1:
                    result = {TASKS_TEMPLATE_PATH: job_results[0]}
                else:
                    job_output_entry: List[Dict[str, Any]] = []
                    for job_result in job_results:
                        job_output_entry.append({TASKS_TEMPLATE_PATH: job_result})
                    result = job_output_entry

                update_job_run_status(
                    wf_run_container,
                    workflow_run,
                    job_def.get_id(),
                    JobRunStatus.COMPLETED,
                )

                return result
        finally:
            logger.info(f"...cleaning up based on task data for job: {job_id}")
            self.task_runner.cleanup([d.runner_info for d in task_data])

    def execute_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:
        workflow_id: str = submit_message.workflow.id
        run_id = submit_message.run_id

        logger.info(f"*** Workflow started *** {workflow_id=}, {run_id=}")

        # trace_parent: Union[str, None] = None
        # trace_state: Union[str, None] = None
        # if submit_message.args is not None:
        #     trace_parent = submit_message.args.get("traceparent")
        #     trace_state = submit_message.args.get("tracestate")

        # otel_detach_token = otel.attach_to_parent(
        #     trace_parent, trace_state, operation_id=run_id
        # )

        # with tracer.start_as_current_span(__name__) as span:
        #     span.set_attribute("operation_id", workflow_id)
        #     span.set_attribute("run_id", run_id)
        try:
            result: Dict[str, Any] = self.execute_workflow_internal(
                submit_message=submit_message
            )
        finally:
            pass
            # if otel_detach_token:
            #     otel.detach(otel_detach_token)

        return result

    def execute_workflow_internal(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:
        workflow = submit_message.get_workflow_with_templated_args()
        trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)
        run_id = submit_message.run_id
        dataset_id = submit_message.workflow.definition.dataset_id
        target_env = workflow.definition.target_environment

        run_settings = self.config.run_settings
        pool = futures.ThreadPoolExecutor(
            max_workers=run_settings.remote_runner_threads
        )

        log_path = get_workflow_log_path(run_id)
        log_uri = (
            f"blob://{run_settings.blob_account_name}/"
            f"{run_settings.log_blob_container}/{log_path}"
        )
        log_storage = run_settings.get_log_storage()
        task_io_storage = run_settings.get_task_io_storage()
        task_log_storage = run_settings.get_log_storage()

        with StorageLogger.from_uri(log_uri, log_storage=log_storage):
            logger.info(f"Logging to: {log_uri}")

            # Create containers
            logger.info("Creating CosmosDB connections...")
            with WorkflowRunsContainer(
                WorkflowRunRecord, db=self.config.get_cosmosdb()
            ) as wf_run_container, WorkflowRunsContainer(
                JobPartitionRunRecord, db=self.config.get_cosmosdb()
            ) as jp_container:
                workflow_run = wf_run_container.get(run_id, partition_key=run_id)

                if not workflow_run:
                    raise WorkflowRunRecordError(
                        f"Record for workflow run {run_id} not found."
                    )

                update_workflow_run_status(
                    wf_run_container,
                    workflow_run,
                    WorkflowRunStatus.RUNNING,
                    log_uri=log_uri,
                )

                job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}
                workflow_failed = False
                try:
                    workflow_jobs = list(workflow.definition.jobs.values())
                    sorted_jobs = sort_jobs(workflow_jobs)
                    len_jobs = len(sorted_jobs)
                    logger.info(f"Running jobs: {[j.id for j in sorted_jobs]}")
                    for job_idx, job_def in enumerate(sorted_jobs):
                        # For each job, create the job partitions
                        # through the task pool, submit all initial
                        # tasks, and then wait for all tasks to complete

                        job_id = job_def.get_id()
                        job_run = workflow_run.get_job_run(job_id)

                        # Track if this is the last job.
                        # If so, there's no reason to hold onto
                        # job outputs. Avoiding this will save
                        # memory.
                        is_last_job = job_idx == len_jobs - 1

                        if not job_run:
                            raise WorkflowRunRecordError(
                                f"Job run {job_def.get_id()} not found."
                            )

                        if workflow_failed:
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.CANCELLED,
                            )
                            # Skip processing the job
                            continue

                        logger.info(f"Running job: {job_def.id}")
                        update_job_run_status(
                            wf_run_container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.RUNNING,
                        )

                        job_partitions: List[JobPartition]

                        # Prepare task data
                        logger.info(f"Preparing task data for job: {job_id}")
                        task_data: List[PreparedTaskData] = []
                        try:
                            for task in job_def.tasks:
                                task_data.append(
                                    prepare_task_data(
                                        dataset_id,
                                        run_id,
                                        job_id,
                                        task,
                                        settings=run_settings,
                                        tokens=workflow.definition.tokens,
                                        target_environment=target_env,
                                        task_runner=self.task_runner,
                                    )
                                )
                        except Exception as e:
                            logger.error(f"Failed to prepare task data: {e}")
                            logger.exception(e)
                            logger.info(
                                f"...cleaning up based on task data for job: {job_id}"
                            )
                            self.task_runner.cleanup([d.runner_info for d in task_data])
                            job_run.add_errors(
                                [
                                    f"Job {job_def.id} failed during task data prep:",
                                    str(e),
                                ]
                            )
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.FAILED,
                            )
                            workflow_failed = True
                            continue

                        try:
                            if job_def.foreach:
                                items = template_foreach(
                                    job_def.foreach,
                                    job_outputs=job_outputs,
                                    trigger_event=None,
                                )
                                job_partitions = [
                                    JobPartition(
                                        definition=template_job_with_item(
                                            job_def, item
                                        ),
                                        partition_id=str(i),
                                        task_data=task_data,
                                    )
                                    for i, item in enumerate(items)
                                ]
                                msg = f" - Running {len(job_partitions)} job partitions"
                                logger.info(msg)
                            else:
                                job_partitions = [
                                    JobPartition(
                                        definition=job_def,
                                        partition_id="0",
                                        task_data=task_data,
                                    )
                                ]
                        except Exception as e:
                            logger.error(f"Failed to template job partitions: {e}")
                            logger.exception(e)
                            logger.info(
                                f"...cleaning up based on task data for job: {job_id}"
                            )
                            self.task_runner.cleanup([d.runner_info for d in task_data])
                            job_run.add_errors(
                                [f"Job {job_def.id} failed during templating.:", str(e)]
                            )
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.FAILED,
                            )
                            workflow_failed = True
                            continue

                        total_job_part_count = len(job_partitions)

                        if total_job_part_count <= 0:
                            job_outputs[job_id] = []
                            logger.warning(f"No tasks, skipping job {job_id}")
                            logger.info(
                                f"...cleaning up based on task data for job: {job_id}"
                            )
                            self.task_runner.cleanup([d.runner_info for d in task_data])
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.SKIPPED,
                                errors=[f"Job {job_def.id} has no partitions to run."],
                            )
                            continue

                        # ## CREATE JOB PARTITIONS

                        job_part_submit_msgs = [
                            JobPartitionSubmitMessage(
                                job_partition=prepared_job,
                                dataset_id=workflow.dataset_id,
                                run_id=submit_message.run_id,
                                job_id=prepared_job.definition.get_id(),
                                partition_id=prepared_job.partition_id,
                                tokens=workflow.definition.tokens,
                                target_environment=target_env,
                                job_outputs=job_outputs,
                                trigger_event=trigger_event,
                            )
                            for prepared_job in job_partitions
                        ]

                        # Create job states, prepare first tasks.
                        logger.info(" - Preparing jobs...")

                        try:
                            job_part_states = self.create_job_partition_states(
                                job_part_submit_msgs, jp_container, workflow.id
                            )
                        except Exception as e:
                            logger.error(f"Failed to prepare job partitions: {e}")
                            logger.exception(e)
                            logger.info(
                                f"...cleaning up based on task data for job: {job_id}"
                            )
                            self.task_runner.cleanup([d.runner_info for d in task_data])
                            logger.exception(e)
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.FAILED,
                                errors=[
                                    f"Job {job_def.id} failed during job preparation.",
                                    str(e),
                                ],
                            )
                            workflow_failed = True
                            continue

                        if any(
                            [
                                jps.status == JobPartitionStateStatus.NOTASKS
                                for jps in job_part_states
                            ]
                        ):
                            # Mark all submitting task as cancelled.
                            try:
                                list(
                                    pool.map(
                                        self.cancel_tasks,
                                        job_part_states,
                                    )
                                )
                            except Exception as e:
                                logger.exception(e)

                            logger.warning(f" - Job {job_id} has no tasks to run.")
                            logger.info(
                                f"...cleaning up based on task data for job: {job_id}"
                            )
                            self.task_runner.cleanup([d.runner_info for d in task_data])

                            # Fail job, update all task records to cancelled or failed.
                            update_job_run_status(
                                wf_run_container,
                                workflow_run,
                                job_def.get_id(),
                                JobRunStatus.FAILED,
                            )
                            workflow_failed = True
                            continue

                        current_job_outputs = self.execute_job_partitions(
                            run_id,
                            job_id,
                            workflow_run,
                            job_def,
                            total_job_part_count,
                            task_data,
                            is_last_job,
                            job_part_states,
                            wf_run_container,
                            jp_container,
                            pool,
                            task_io_storage,
                            task_log_storage,
                        )

                        if current_job_outputs is None:
                            workflow_failed = True
                        else:
                            job_outputs[job_id] = current_job_outputs

                    if workflow_failed:
                        logger.error("Workflow failed!")
                        # The workflow will be marked as failed in the except block
                        # update_workflow_run_status(
                        #     wf_run_container,
                        #     op_container,
                        #     tracking_container,
                        #     workflow_run,
                        #     WorkflowRunStatus.FAILED,
                        # )
                        raise WorkflowFailedError(f"Workflow '{workflow.id}' failed.")
                    else:
                        logger.info("Workflow completed!")
                        update_workflow_run_status(
                            wf_run_container,
                            workflow_run,
                            WorkflowRunStatus.COMPLETED,
                        )
                except Exception as e:
                    logger.exception(e)
                    update_workflow_run_status(
                        wf_run_container,
                        workflow_run,
                        WorkflowRunStatus.FAILED,
                    )

                return job_outputs
