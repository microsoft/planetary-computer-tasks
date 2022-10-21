import logging
import math
import random
import time
from concurrent import futures
from typing import Any, Dict, List, Optional, Tuple, Union

from pctasks.core.cosmos.containers.workflow_runs import WorkflowRunsContainer
from pctasks.core.logging import StorageLogger
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.core.models.run import (
    JobPartition,
    JobPartitionRunRecord,
    JobPartitionRunStatus,
    JobRunStatus,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import CompletedTaskResult, FailedTaskResult
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.queues import QueueService
from pctasks.core.utils import grouped, map_opt
from pctasks.run.constants import TASKS_TEMPLATE_PATH
from pctasks.run.dag import sort_jobs
from pctasks.run.errors import WorkflowRunRecordError
from pctasks.run.models import (
    FailedTaskSubmitResult,
    JobPartitionSubmitMessage,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
)
from pctasks.run.settings import WorkflowExecutorConfig
from pctasks.run.task import get_task_runner
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


class RemoteWorkflowRunnerError(Exception):
    pass


class WorkflowFailedError(Exception):
    pass


def update_workflow_run_status(
    container: WorkflowRunsContainer[WorkflowRunRecord],
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


def update_job_run_status(
    container: WorkflowRunsContainer[WorkflowRunRecord],
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


def update_job_partition_run_status(
    container: WorkflowRunsContainer[JobPartitionRunRecord],
    job_partition_run: JobPartitionRunRecord,
    status: JobPartitionRunStatus,
) -> None:
    record = container.get(
        job_partition_run.get_id(), partition_key=job_partition_run.run_id
    )
    if not record:
        raise WorkflowRunRecordError(
            f"Job Partition run record not found: {job_partition_run.get_id()}"
        )
    if record.status != status:
        record.set_status(status)
        container.put(record)


def update_task_run_status(
    container: WorkflowRunsContainer[JobPartitionRunRecord],
    job_partition_run: JobPartitionRunRecord,
    task_id: str,
    status: TaskRunStatus,
    errors: Optional[List[str]] = None,
    log_uri: Optional[str] = None,
) -> None:
    record = container.get(
        job_partition_run.get_id(), partition_key=job_partition_run.run_id
    )
    if not record:
        raise WorkflowRunRecordError(
            f"Job Partition run record not found: {job_partition_run.get_id()}"
        )

    task_run = record.get_task(task_id)
    if not task_run:
        raise WorkflowRunRecordError(
            f"Task run not found: {job_partition_run.get_id()} {task_id}"
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


class RemoteWorkflowExecutor:
    """Executes a workflow through submitting tasks remotely via a task runner."""

    def __init__(self, settings: Optional[WorkflowExecutorConfig] = None) -> None:
        self.config = settings or WorkflowExecutorConfig.get()
        self.executor = get_task_runner(self.config.run_settings)

    def create_job_partition_state(
        self, submit_msg: JobPartitionSubmitMessage
    ) -> JobPartitionState:
        """Create a job state from a job submit message."""
        job_partition_run = JobPartitionRunRecord.from_job_partition(
            submit_msg.job_partition,
            submit_msg.run_id,
            status=JobPartitionRunStatus.RUNNING,
        )

        container = WorkflowRunsContainer(
            JobPartitionRunRecord, db=self.config.get_cosmosdb()
        )

        job_partition_state = JobPartitionState.create(
            submit_msg,
            job_part_run_record_id=job_partition_run.get_id(),
            settings=self.config.run_settings,
        )

        try:
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
        finally:
            container.put(job_partition_run)

        return job_partition_state

    def send_notification(
        self, notification_submit_message: NotificationSubmitMessage
    ) -> None:
        """Send a notification to the notification queue."""
        queue_settings = self.config.run_settings.notification_queue
        with QueueService.from_connection_string(
            connection_string=queue_settings.connection_string,
            queue_name=queue_settings.queue_name,
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
        container: Optional[WorkflowRunsContainer[JobPartitionRunRecord]] = None,
        job_part_run: Optional[JobPartitionRunRecord] = None,
    ) -> TaskRunStatus:
        """Updates a task state and task run status based on the submit result.

        Returns the resulting task run status.
        """
        container = container or WorkflowRunsContainer(
            JobPartitionRunRecord, db=self.config.get_cosmosdb()
        )
        job_part_run = job_part_run or container.get(
            task_state.job_part_run_record_id, partition_key=task_state.run_id
        )
        task_state.set_submitted(submit_result)
        if job_part_run:
            if isinstance(submit_result, FailedTaskSubmitResult):
                update_task_run_status(
                    container,
                    job_part_run,
                    task_state.task_id,
                    TaskRunStatus.FAILED,
                    errors=["Task failed to submit."] + submit_result.errors,
                )
                return TaskRunStatus.FAILED
            else:
                update_task_run_status(
                    container,
                    job_part_run,
                    task_state.task_id,
                    TaskRunStatus.SUBMITTED,
                )
                return TaskRunStatus.SUBMITTED
        else:
            return TaskRunStatus.FAILED

    def complete_job_partitions(
        self,
        run_id: str,
        job_id: str,
        part_id: str,
        job_part_states: List[JobPartitionState],
    ) -> List[Dict[str, Any]]:
        """Complete job partitions and return the results.

        This is a blocking loop that is meant to be called on it's own thread.
        """
        task_io_storage = self.config.run_settings.get_task_io_storage()
        task_log_storage = self.config.run_settings.get_log_storage()

        completed_job_count = 0
        failed_job_count = 0
        total_job_count = len(job_part_states)
        _jobs_left = lambda: total_job_count - completed_job_count - failed_job_count
        _report_status = lambda: logger.info(
            f"{job_id} {part_id} status: "
            f"{completed_job_count} completed, "
            f"{failed_job_count} failed, "
            f"{_jobs_left()} remaining"
        )

        container = WorkflowRunsContainer(
            JobPartitionRunRecord, db=self.config.get_cosmosdb()
        )
        job_part_runs: Dict[str, JobPartitionRunRecord] = {}

        while _jobs_left() > 0:
            for job_part_state in job_part_states:
                try:
                    if job_part_state.status == JobPartitionStateStatus.NEW:
                        job_part_state.status = JobPartitionStateStatus.RUNNING

                        # Job Partition Run already set to status running.
                        # Record the job part run here for later updates.
                        job_part_run = container.get(
                            job_part_state.job_part_run_record_id, partition_key=run_id
                        )
                        if not job_part_run:
                            raise WorkflowRunRecordError(
                                "Job partition run not found: "
                                f"{job_part_state.job_part_run_record_id}"
                            )
                        job_part_runs[part_id] = job_part_run

                    if job_part_state.current_task:
                        task_state = job_part_state.current_task

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

                        # If not completed through output or status update,
                        # poll the executor in case of other failure.
                        if task_state.should_poll(
                            self.config.run_settings.task_poll_seconds
                        ):
                            logger.debug(
                                f" ~ Polling {job_part_state.job_id}:"
                                f"{task_state.task_id}"
                            )
                            task_state.poll(
                                self.executor, task_io_storage, self.config.run_settings
                            )

                        #
                        # Act on task state
                        #

                        if task_state.status == TaskStateStatus.NEW:

                            # New task, submit it

                            update_task_run_status(
                                container,
                                job_part_runs[part_id],
                                task_state.task_id,
                                TaskRunStatus.SUBMITTING,
                            )

                            job_part_state.current_task.submit(self.executor)
                            submit_result = job_part_state.current_task.submit_result
                            if not submit_result:
                                raise Exception(
                                    f"Unexpected submit result: {submit_result}"
                                )

                            self.update_submit_result(
                                task_state,
                                submit_result,
                                container,
                                job_part_runs[part_id],
                            )

                        elif task_state.status == TaskStateStatus.SUBMITTED:

                            # Job is running...
                            pass

                        elif task_state.status == TaskStateStatus.RUNNING:

                            # Job is still running...
                            if not task_state.status_updated:
                                update_task_run_status(
                                    container,
                                    job_part_runs[part_id],
                                    task_state.task_id,
                                    TaskRunStatus.RUNNING,
                                )
                                task_state.status_updated = True

                        elif task_state.status == TaskStateStatus.WAITING:

                            # If we just moved the job state to waiting,
                            # update the record.

                            if not task_state.status_updated:
                                update_task_run_status(
                                    container,
                                    job_part_runs[part_id],
                                    task_state.task_id,
                                    TaskRunStatus.WAITING,
                                )
                                task_state.status_updated = True

                        elif task_state.status == TaskStateStatus.FAILED:

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
                                job_part_runs[part_id],
                                task_state.task_id,
                                TaskRunStatus.FAILED,
                                errors=errors,
                                log_uri=task_state.get_log_uri(task_log_storage),
                            )

                            logger.warning(
                                "Job partition failed: "
                                f"{job_part_state.job_id}:{part_id}"
                            )

                            _report_status()

                        elif task_state.status == TaskStateStatus.COMPLETED:

                            logger.info(
                                f"Task completed: {job_part_state.job_id} "
                                f"- {task_state.task_id}"
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

                            job_part_state.task_outputs[task_state.task_id] = {
                                "output": task_state.task_result.output
                            }

                            update_task_run_status(
                                container,
                                job_part_runs[part_id],
                                task_state.task_id,
                                TaskRunStatus.COMPLETED,
                                log_uri=task_state.get_log_uri(task_log_storage),
                            )

                            try:
                                job_part_state.prepare_next_task(
                                    self.config.run_settings
                                )
                            except Exception:
                                job_part_state.status = JobPartitionStateStatus.FAILED
                                failed_job_count += 1
                                update_job_partition_run_status(
                                    container,
                                    job_part_runs[part_id],
                                    JobPartitionRunStatus.FAILED,
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
                                        job_part_runs[part_id],
                                        JobPartitionRunStatus.COMPLETED,
                                    )
                                    self.handle_job_part_notifications(job_part_state)
                                except Exception:
                                    job_part_state.status = (
                                        JobPartitionStateStatus.FAILED
                                    )
                                    failed_job_count += 1
                                    update_job_partition_run_status(
                                        container,
                                        job_part_runs[part_id],
                                        JobPartitionRunStatus.FAILED,
                                    )
                                completed_job_count += 1
                                logger.info(f"Job completed: {job_id}")

                            _report_status()

                except Exception as e:
                    logger.exception(e)
                    raise

            time.sleep(0.25 + ((random.randint(0, 10) / 100) - 0.05))

        logger.info(f"Task group {part_id} completed!")

        return [job_state.task_outputs for job_state in job_part_states]

    def execute_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:

        workflow = submit_message.get_workflow_with_templated_args()
        trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)
        run_id = submit_message.run_id

        pool = futures.ThreadPoolExecutor(
            max_workers=self.config.run_settings.remote_runner_threads
        )

        log_path = get_workflow_log_path(run_id)
        log_uri = (
            f"blob://{self.config.run_settings.blob_account_name}/"
            f"{self.config.run_settings.log_blob_container}/{log_path}"
        )
        log_storage = self.config.run_settings.get_log_storage()

        with StorageLogger.from_uri(log_uri, log_storage=log_storage):

            logger.info("***********************************")
            logger.info(f"Workflow: {submit_message.workflow.id}")
            logger.info(f"Run Id: {run_id}")
            logger.info("***********************************")

            logger.info(f"Logging to: {log_uri}")

            container = WorkflowRunsContainer(
                WorkflowRunRecord, db=self.config.get_cosmosdb()
            )
            workflow_run = container.get(run_id, partition_key=run_id)

            if not workflow_run:
                raise WorkflowRunRecordError(
                    f"Record for workflow run {run_id} not found."
                )

            update_workflow_run_status(
                container, workflow_run, WorkflowRunStatus.RUNNING, log_uri=log_uri
            )

            job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}
            workflow_failed = False
            try:

                workflow_jobs = list(workflow.definition.jobs.values())
                sorted_jobs = sort_jobs(workflow_jobs)
                logger.info(f"Running jobs: {[j.id for j in sorted_jobs]}")
                for job_def in sorted_jobs:

                    # For each job, create the job partitions
                    # through the task pool, submit all initial
                    # tasks, and then wait for all tasks to complete

                    job_id = job_def.get_id()
                    job_run = workflow_run.get_job_run(job_id)

                    if not job_run:
                        raise WorkflowRunRecordError(
                            f"Job run {job_def.get_id()} not found."
                        )

                    if workflow_failed:
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.CANCELLED,
                        )
                        # Skip processing the job
                        continue

                    logger.info(f"Running job: {job_def.id}")
                    update_job_run_status(
                        container, workflow_run, job_def.get_id(), JobRunStatus.RUNNING
                    )

                    job_partitions: List[JobPartition]
                    try:
                        if job_def.foreach:
                            items = template_foreach(
                                job_def.foreach,
                                job_outputs=job_outputs,
                                trigger_event=None,
                            )
                            job_partitions = [
                                JobPartition(
                                    definition=template_job_with_item(job_def, item),
                                    partition_id=str(i),
                                )
                                for i, item in enumerate(items)
                            ]
                            msg = f" - Running {len(job_partitions)} job partitions"
                            logger.info(msg)
                        else:
                            job_partitions = [
                                JobPartition(definition=job_def, partition_id="0")
                            ]
                    except Exception as e:
                        logger.exception(e)
                        job_run.add_errors(
                            [f"Job {job_def.id} failed during templating.:", str(e)]
                        )
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.FAILED,
                        )
                        workflow_failed = True
                        continue

                    total_job_part_count = len(job_partitions)

                    if total_job_part_count <= 0:
                        job_outputs[job_id] = []
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.SKIPPED,
                            errors=[f"Job {job_def.id} has no partitions to run."],
                        )
                        continue

                    job_submit_messages = [
                        JobPartitionSubmitMessage(
                            job_partition=prepared_job,
                            dataset_id=workflow.dataset_id,
                            run_id=submit_message.run_id,
                            job_id=prepared_job.definition.get_id(),
                            partition_id=prepared_job.partition_id,
                            tokens=workflow.definition.tokens,
                            target_environment=workflow.definition.target_environment,
                            job_outputs=job_outputs,
                            trigger_event=trigger_event,
                        )
                        for prepared_job in job_partitions
                    ]

                    # Create job states, prepare first tasks.
                    logger.info(" - Preparing jobs...")
                    try:
                        job_part_states = list(
                            pool.map(
                                self.create_job_partition_state,
                                job_submit_messages,
                            )
                        )
                    except Exception as e:
                        logger.exception(e)
                        update_job_run_status(
                            container,
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

                        # Fail job, update all task records to cancelled or failed.
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.FAILED,
                        )
                        workflow_failed = True
                        continue

                    initial_tasks: List[PreparedTaskSubmitMessage] = []
                    for job_part_state in job_part_states:
                        # Case with no tasks has already been handled.
                        assert job_part_state.current_task
                        initial_tasks.append(job_part_state.current_task.prepared_task)

                    # First tasks in a job are submitted in bulk to minimize
                    # the number of concurrent API calls.
                    logger.info(" - Submitting initial tasks...")
                    submit_results = self.executor.submit_tasks(initial_tasks)

                    logger.info(" -  Initial tasks submitted, checking status...")

                    try:

                        def _update_submit_results(
                            tup: Tuple[
                                JobPartitionState,
                                Union[
                                    SuccessfulTaskSubmitResult, FailedTaskSubmitResult
                                ],
                            ]
                        ) -> TaskRunStatus:
                            jps, submit_result = tup
                            assert jps.current_task
                            return self.update_submit_result(
                                jps.current_task, submit_result
                            )

                        any_submitted = False
                        all_submitted = True
                        for submitted in pool.map(
                            _update_submit_results,
                            zip(job_part_states, submit_results),
                        ):
                            _this_task_submitted = submitted == TaskRunStatus.SUBMITTED
                            any_submitted = any_submitted or _this_task_submitted
                            all_submitted = all_submitted and _this_task_submitted

                        if all_submitted:
                            logger.info(" -  All initial tasks submitted successfully.")
                        elif any_submitted:
                            logger.info(
                                " -  Some (not all) initial tasks "
                                "submitted successfully."
                            )

                    except Exception as e:
                        logger.exception(e)
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.FAILED,
                        )
                        workflow_failed = True
                        continue

                    if not any_submitted:
                        logger.info(" -  All initial tasks failed to submit.")
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.FAILED,
                            errors=[
                                f"Failed to submit tasks for job {job_def.get_id()}"
                            ],
                        )
                        workflow_failed = True
                        continue

                    # Split the job partitions into groups based on number of threads
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

                    # Wait for the first task of the job partition to complete,
                    # and then complete all remaining tasks

                    logger.info("Waiting for tasks to complete...")

                    job_part_futures = {
                        pool.submit(
                            self.complete_job_partitions,
                            run_id,
                            job_id,
                            f"job-part-group-{group_num}",
                            job_state_group,
                        ): job_state_group
                        for job_state_group, group_num in grouped_job_partition_states
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
                                str(f"Job partitions thread failed with {future_error}")
                            )

                        job_done_count += len(job_part_states)
                        for job_part_state in job_part_states:
                            if job_part_state.status == JobPartitionStateStatus.FAILED:
                                job_failed = True
                            else:
                                job_results.append(job_part_state.task_outputs)

                        logger.info(
                            f"Job {job_id} partition progress: "
                            f"({job_done_count}/{total_job_part_count})"
                        )

                    if job_failed:
                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.FAILED,
                            errors=failed_job_part_errors,
                        )
                        workflow_failed = True
                    else:
                        if len(job_results) == 1:
                            job_outputs[job_id] = {TASKS_TEMPLATE_PATH: job_results[0]}
                        else:
                            job_output_entry: List[Dict[str, Any]] = []
                            for job_result in job_results:
                                job_output_entry.append(
                                    {TASKS_TEMPLATE_PATH: job_result}
                                )
                            job_outputs[job_id] = job_output_entry

                        update_job_run_status(
                            container,
                            workflow_run,
                            job_def.get_id(),
                            JobRunStatus.COMPLETED,
                        )

                if workflow_failed:
                    logger.error("Workflow failed!")
                    update_workflow_run_status(
                        container, workflow_run, WorkflowRunStatus.FAILED
                    )
                    raise WorkflowFailedError(f"Workflow '{workflow.id}' failed.")
                else:
                    logger.info("Workflow completed!")
                    update_workflow_run_status(
                        container, workflow_run, WorkflowRunStatus.COMPLETED
                    )
            except Exception as e:
                logger.exception(e)
                update_workflow_run_status(
                    container, workflow_run, WorkflowRunStatus.FAILED
                )

            return job_outputs
