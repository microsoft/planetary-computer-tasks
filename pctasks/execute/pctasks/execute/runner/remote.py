import logging
import math
import random
import time
from concurrent import futures
from typing import Any, Dict, List, Optional, Set, Union

from pctasks.core.logging import RunLogger
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.core.models.record import (
    JobRunRecord,
    JobRunStatus,
    TaskRunRecord,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import CompletedTaskResult
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.queues import QueueService
from pctasks.core.utils import grouped, map_opt
from pctasks.execute.constants import TASKS_TEMPLATE_PATH
from pctasks.execute.dag import sort_jobs
from pctasks.execute.executor import get_executor
from pctasks.execute.models import (
    FailedSubmitResult,
    JobRunRecordUpdate,
    JobSubmitMessage,
    PreparedTaskSubmitMessage,
    SuccessfulSubmitResult,
    TaskRunRecordUpdate,
    WorkflowRunRecordUpdate,
)
from pctasks.execute.records import RecordUpdater
from pctasks.execute.runner.models import (
    JobState,
    JobStateStatus,
    TaskState,
    TaskStateStatus,
)
from pctasks.execute.settings import ExecuteSettings
from pctasks.execute.template import (
    template_foreach,
    template_job_with_item,
    template_notification,
)

logger = logging.getLogger(__name__)


class RemoteRunnerError(Exception):
    pass


class WorkflowFailedError(Exception):
    pass


class RemoteRunner:
    """Runs a workflow through executing tasks remotely via a task executor."""

    def __init__(self, settings: Optional[ExecuteSettings] = None) -> None:
        self.settings = settings or ExecuteSettings.get()
        self.executor = get_executor(self.settings)
        self.record_updater = RecordUpdater(self.settings)

    def create_job_state(self, job_submit_message: JobSubmitMessage) -> JobState:
        """Create a job state from a job submit message."""
        job_state = JobState.create(job_submit_message, self.settings)
        self.record_updater.upsert_record(
            record=JobRunRecord(
                run_id=job_state.job_submit_message.run_id,
                job_id=job_state.job_id,
                status=JobRunStatus.RUNNING,
            )
        )

        if job_state.current_task:
            task_state = job_state.current_task
            self.record_updater.upsert_record(
                record=TaskRunRecord(
                    run_id=task_state.prepared_task.task_submit_message.run_id,
                    job_id=task_state.prepared_task.task_submit_message.job_id,
                    task_id=task_state.task_id,
                    status=TaskRunStatus.SUBMITTING,
                )
            )

        return job_state

    def update_submitted_task_state(
        self,
        task_state: TaskState,
        submit_result: Union[SuccessfulSubmitResult, FailedSubmitResult],
    ) -> None:
        task_state.set_submitted(submit_result)

        if isinstance(submit_result, FailedSubmitResult):
            self.record_updater.update_record(
                TaskRunRecordUpdate(
                    run_id=task_state.prepared_task.task_submit_message.run_id,
                    job_id=task_state.prepared_task.task_submit_message.job_id,
                    task_id=task_state.task_id,
                    status=TaskRunStatus.FAILED,
                    errors=[
                        "Failed to submit task.",
                    ]
                    + submit_result.errors,
                )
            )
        else:
            self.record_updater.update_record(
                TaskRunRecordUpdate(
                    run_id=task_state.prepared_task.task_submit_message.run_id,
                    job_id=task_state.prepared_task.task_submit_message.job_id,
                    task_id=task_state.task_id,
                    status=TaskRunStatus.SUBMITTING,
                )
            )

    def send_notification(
        self, notification_submit_message: NotificationSubmitMessage
    ) -> None:
        """Send a notification to the notification queue."""
        queue_settings = self.settings.notification_queue
        with QueueService.from_connection_string(
            connection_string=queue_settings.connection_string,
            queue_name=queue_settings.queue_name,
        ) as queue:
            msg_id = queue.send_message(notification_submit_message.dict())
            logger.info(f"  - Notification sent, queue id {msg_id}")

    def succeed_job(self, job_state: JobState) -> None:
        job_state.status = JobStateStatus.SUCCEEDED

        self.record_updater.update_record(
            JobRunRecordUpdate(
                status=JobRunStatus.COMPLETED,
                run_id=job_state.job_submit_message.run_id,
                job_id=job_state.job_id,
            )
        )

        # Handle job notifications

        job_submit_msg = job_state.job_submit_message
        job_config = job_submit_msg.job
        if job_config.notifications:
            for notification in job_config.notifications:
                templated_notification = template_notification(
                    notification=notification,
                    task_outputs=job_state.task_outputs,
                )
                notification_message = templated_notification.to_message()
                notification_submit_msg = NotificationSubmitMessage(
                    notification=notification_message,
                    target_environment=job_submit_msg.target_environment,
                    processing_id=job_state.job_submit_message.get_run_record_id(),
                )

                self.send_notification(notification_submit_msg)

    def complete_jobs(
        self, run_id: str, group_id: str, job_states: List[JobState]
    ) -> List[Dict[str, Any]]:
        """Complete jobs and return the results.

        This is a blocking loop that is meant to be called on it's own thread.
        """
        task_io_storage = self.settings.get_task_io_storage()
        task_log_storage = self.settings.get_log_storage()

        completed_job_count = 0
        failed_job_count = 0
        total_job_count = len(job_states)
        _jobs_left = lambda: total_job_count - completed_job_count - failed_job_count
        _report_status = lambda: logger.info(
            f"{group_id} status: "
            f"{completed_job_count} completed, "
            f"{failed_job_count} failed, "
            f"{_jobs_left()} remaining"
        )

        while _jobs_left():
            # print(f"{group_id} remaining: {_jobs_left()}")
            statuses: List[str] = []
            for job_state in job_states:
                if job_state.status == JobStateStatus.NEW:
                    job_state.status = JobStateStatus.RUNNING
                    self.record_updater.upsert_record(
                        record=JobRunRecord(
                            status=JobRunStatus.RUNNING,
                            run_id=run_id,
                            job_id=job_state.job_id,
                        )
                    )

                if job_state.current_task:
                    task_state = job_state.current_task

                    #
                    # Update task state
                    #

                    # Update task state if waiting and
                    # wait time expired, sets status to NEW
                    task_state.update_if_waiting()

                    if task_state.should_check_output(
                        self.settings.check_output_seconds
                    ):
                        task_state.process_output_if_available(
                            task_io_storage, self.settings
                        )

                    # If not completed through output, poll
                    # the executor in case of other failure.
                    if task_state.should_poll(self.settings.task_poll_seconds):
                        print(f" ~ Polling {job_state.job_id}:{task_state.task_id}")
                        task_state.poll(self.executor, task_io_storage, self.settings)

                    #
                    # Act on task state
                    #

                    if task_state.status == TaskStateStatus.NEW:

                        # New task, submit it

                        self.record_updater.upsert_record(
                            record=TaskRunRecord(
                                run_id=task_state.run_id,
                                job_id=task_state.job_id,
                                task_id=task_state.task_id,
                                status=TaskRunStatus.SUBMITTING,
                            )
                        )
                        job_state.current_task.submit(self.executor)
                        submit_result = job_state.current_task.submit_result
                        if not submit_result:
                            raise Exception(
                                f"Unexpected submit result: {submit_result}"
                            )

                        self.update_submitted_task_state(task_state, submit_result)

                    elif task_state.status == TaskStateStatus.SUBMITTED:

                        # Job is still running...
                        pass

                    elif task_state.status == TaskStateStatus.WAITING:

                        # If we just moved the job state to waiting,
                        # update the record.

                        if not task_state.status_updated:
                            self.record_updater.update_record(
                                TaskRunRecordUpdate(
                                    status=TaskRunStatus.WAITING,
                                    run_id=run_id,
                                    job_id=job_state.job_id,
                                    task_id=task_state.task_id,
                                )
                            )
                            task_state.status_updated = True

                    elif task_state.status == TaskStateStatus.FAILED:

                        logger.warning(
                            f"Task failed: {job_state.job_id} - {task_state.task_id}"
                        )

                        failed_job_count += 1

                        job_state.status = JobStateStatus.FAILED
                        job_state.current_task = None

                        # Mark this task as failed

                        self.record_updater.update_record(
                            TaskRunRecordUpdate(
                                status=TaskRunStatus.FAILED,
                                run_id=run_id,
                                job_id=job_state.job_id,
                                task_id=task_state.task_id,
                                log_uris=map_opt(
                                    lambda uri: [uri],
                                    task_state.get_log_uri(task_log_storage),
                                ),
                            )
                        )

                        # Mark any other tasks in the job as cancelled
                        for task_config in job_state.task_queue:
                            self.record_updater.upsert_record(
                                record=TaskRunRecord(
                                    status=TaskRunStatus.CANCELLED,
                                    run_id=run_id,
                                    job_id=job_state.job_id,
                                    task_id=task_config.id,
                                )
                            )

                        job_state.status = JobStateStatus.FAILED

                        self.record_updater.update_record(
                            JobRunRecordUpdate(
                                status=JobRunStatus.FAILED,
                                run_id=run_id,
                                job_id=job_state.job_id,
                                errors=[f"Task {task_state.task_id} failed"],
                            )
                        )

                        logger.warning(f"Job failed: {job_state.job_id}")

                        _report_status()

                    elif task_state.status == TaskStateStatus.COMPLETED:

                        logger.info(
                            f"Task completed: {job_state.job_id} - {task_state.task_id}"
                        )
                        assert isinstance(task_state.task_result, CompletedTaskResult)
                        job_state.task_outputs[task_state.task_id] = {
                            "output": task_state.task_result.output
                        }

                        self.record_updater.update_record(
                            TaskRunRecordUpdate(
                                status=TaskRunStatus.COMPLETED,
                                run_id=run_id,
                                job_id=job_state.job_id,
                                task_id=task_state.task_id,
                                log_uris=map_opt(
                                    lambda uri: [uri],
                                    task_state.get_log_uri(task_log_storage),
                                ),
                            )
                        )

                        job_state.prepare_next_task(self.settings)

                        # Handle job completion
                        if job_state.current_task is None:
                            try:
                                self.succeed_job(job_state)
                                completed_job_count += 1
                                logger.info(f"Job completed: {job_state.job_id}")
                            except Exception as e:
                                job_state.status = JobStateStatus.FAILED
                                failed_job_count += 1
                                self.record_updater.update_record(
                                    JobRunRecordUpdate(
                                        status=JobRunStatus.FAILED,
                                        run_id=run_id,
                                        job_id=job_state.job_id,
                                        errors=[
                                            (
                                                f"Job {job_state.job_id} "
                                                "failed while completing"
                                            ),
                                            str(e),
                                        ],
                                    )
                                )

                        _report_status()
                    statuses.append(
                        f"{job_state.job_id}:{task_state.task_id}:{task_state.status}"
                    )

            # for status in statuses:
            #     print(f"- {status}")
            time.sleep(0.25 + ((random.randint(0, 10) / 100) - 0.05))

        logger.info(f"Task group {group_id} completed!")

        return [job_state.task_outputs for job_state in job_states]

    def run_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:
        """Runs a workflow through executing tasks in Azure Batch."""

        workflow = submit_message.get_workflow_with_templated_args()
        run_record_id = submit_message.get_run_record_id()
        run_logger = RunLogger(run_record_id, logger_id="RUNNER")
        trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)
        run_id = submit_message.run_id

        pool = futures.ThreadPoolExecutor(
            max_workers=self.settings.remote_runner_threads
        )

        logger.info("***********************************")
        logger.info(f"Workflow: {submit_message.workflow.name}")
        logger.info(f"Run Id: {run_id}")
        logger.info("***********************************")

        # TODO: Reminder: Create RECEIVED/SUBMITTED Workflow record in Azure Function

        self.record_updater.upsert_record(
            record=WorkflowRunRecord(
                dataset=submit_message.workflow.get_dataset_id(),
                run_id=submit_message.run_id,
                workflow=submit_message.workflow,
                trigger_event=submit_message.trigger_event,
                args=submit_message.args,
                status=WorkflowRunStatus.RUNNING,
            ),
        )

        workflow_errors: List[str] = []
        job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}

        workflow_jobs = list(workflow.jobs.values())
        sorted_jobs = sort_jobs(workflow_jobs)
        logger.info(f"Running jobs: {[j.id for j in sorted_jobs]}")
        for base_job in sorted_jobs:
            if workflow_errors:
                break

            msg = f"Running job: {base_job.id}"
            logger.info(msg)
            run_logger.info(msg)

            if base_job.foreach:
                items = template_foreach(
                    base_job.foreach,
                    job_outputs=job_outputs,
                    trigger_event=None,
                )
                jobs = [
                    template_job_with_item(base_job, item, i)
                    for i, item in enumerate(items)
                ]
                msg = f" - Running {len(jobs)} subjobs"
                logger.info(msg)
                run_logger.info(msg)
            else:
                jobs = [base_job]

            total_job_count = len(jobs)

            job_submit_messages = [
                JobSubmitMessage(
                    job=prepared_job,
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    job_id=prepared_job.get_id(),
                    tokens=workflow.tokens,
                    target_environment=workflow.target_environment,
                    job_outputs=job_outputs,
                    trigger_event=trigger_event,
                )
                for prepared_job in jobs
            ]

            # Create job states, prepare first tasks.
            logger.info(" - Preparing jobs...")
            job_states = list(
                pool.map(
                    self.create_job_state,
                    job_submit_messages,
                )
            )
            initial_tasks: List[PreparedTaskSubmitMessage] = []
            for job_state in job_states:
                if not job_state.current_task:
                    raise Exception(
                        f"Job {job_state.job_submit_message.job.id} has no tasks."
                    )
                initial_tasks.append(job_state.current_task.prepared_task)

            # First tasks in a job are submitted in bulk to minimize
            # the number of concurrent API calls.
            logger.info(" - Submitting initial tasks...")
            submit_results = self.executor.submit_tasks(initial_tasks)
            logger.info(" -  Initial tasks submitted.")
            submit_failed = False
            for job_state, submit_result in zip(job_states, submit_results):
                assert job_state.current_task
                self.update_submitted_task_state(job_state.current_task, submit_result)
                if isinstance(submit_result, FailedSubmitResult):
                    print(f"Failed to submit task: {submit_result.errors}")
                    submit_failed = True

            if submit_failed:
                error_msg = f"Failed to submit tasks for job {base_job.id}"
                self.record_updater.update_record(
                    update=WorkflowRunRecordUpdate(
                        status=WorkflowRunStatus.FAILED,
                        dataset=submit_message.workflow.get_dataset_id(),
                        run_id=submit_message.run_id,
                        errors=[error_msg],
                    )
                )
                raise RemoteRunnerError(error_msg)

            # Split the jobs into groups based on number of threads
            grouped_jobs = [
                (list(g), group_num)
                for group_num, g in enumerate(
                    grouped(
                        job_states,
                        int(
                            math.ceil(
                                len(job_states) / self.settings.remote_runner_threads
                            )
                        ),
                    )
                )
            ]

            # Wait for the first task of the job to complete, and then complete
            # all remaining tasks

            logger.info("Waiting for tasks to complete...")

            # TODO: REMOVE
            for group, group_num in grouped_jobs:
                print(f"Group {group_num}")
                for job_state in group:
                    print(f" - {job_state.job_id}")

            job_futures = {
                pool.submit(
                    self.complete_jobs,
                    run_id,
                    f"job-group-{group_num}",
                    job_state_group,
                ): job_state_group
                for job_state_group, group_num in grouped_jobs
            }

            job_results: List[Dict[str, Any]] = []

            job_done_count = 0
            failed_jobs: Set[str] = set()
            for job_future in futures.as_completed(job_futures.keys()):
                job_states = job_futures[job_future]

                future_error = job_future.exception()
                if future_error:
                    self.record_updater.update_record(
                        update=WorkflowRunRecordUpdate(
                            status=WorkflowRunStatus.FAILED,
                            dataset=submit_message.workflow.get_dataset_id(),
                            run_id=submit_message.run_id,
                            errors=[
                                "Unexpected error in workflow runner",
                                str(future_error),
                            ],
                        )
                    )
                    raise future_error

                if job_future.cancelled():
                    self.record_updater.update_record(
                        update=WorkflowRunRecordUpdate(
                            status=WorkflowRunStatus.FAILED,
                            dataset=submit_message.workflow.get_dataset_id(),
                            run_id=submit_message.run_id,
                            errors=[str("Job threads were cancelled.")],
                        )
                    )
                    raise Exception("Jobs were cancelled.")

                job_done_count += len(job_states)
                for job_state in job_states:
                    if job_state.status == JobStateStatus.FAILED:
                        failed_jobs.add(job_state.job_id)
                    else:
                        job_results.append(job_state.task_outputs)

                logger.info(f"Jobs progress: ({job_done_count}/{total_job_count})")

            if failed_jobs:
                workflow_errors.extend(
                    [f"Job failed: {job_id}" for job_id in failed_jobs]
                )
            else:
                if len(job_results) == 1:
                    job_outputs[base_job.get_id()] = {
                        TASKS_TEMPLATE_PATH: job_results[0]
                    }
                else:
                    job_output_entry: List[Dict[str, Any]] = []
                    for job_result in job_results:
                        job_output_entry.append({TASKS_TEMPLATE_PATH: job_result})
                    job_outputs[base_job.get_id()] = job_output_entry

        if workflow_errors:
            logger.info("Workflow failed!")
            self.record_updater.update_record(
                WorkflowRunRecordUpdate(
                    dataset=workflow.get_dataset_id(),
                    run_id=run_id,
                    status=WorkflowRunStatus.FAILED,
                    errors=workflow_errors,
                )
            )
            raise WorkflowFailedError(f"Workflow '{workflow.name}' failed.")
        else:
            logger.info("Workflow completed!")
            self.record_updater.update_record(
                WorkflowRunRecordUpdate(
                    dataset=workflow.get_dataset_id(),
                    run_id=run_id,
                    status=WorkflowRunStatus.COMPLETED,
                )
            )

        return job_outputs
