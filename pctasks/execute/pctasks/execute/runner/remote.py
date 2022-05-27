import json
import logging
import time
from concurrent import futures
from typing import Any, Dict, List, Optional, Union

from pctasks.core.logging import RunLogger
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.record import (
    JobRunStatus,
    TaskRunRecord,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskConfig,
    TaskResult,
    WaitTaskResult,
)
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.storage.base import Storage
from pctasks.core.utils import map_opt
from pctasks.execute.constants import TASKS_TEMPLATE_PATH
from pctasks.execute.dag import sort_jobs
from pctasks.execute.errors import TaskFailedError
from pctasks.execute.executor import get_executor
from pctasks.execute.executor.base import TaskExecutor
from pctasks.execute.models import (
    CreateJobRunRecordUpdate,
    CreateTaskRunRecordUpdate,
    CreateWorkflowRunGroupRecordUpdate,
    CreateWorkflowRunRecordUpdate,
    FailedSubmitResult,
    JobRunRecordUpdate,
    JobSubmitMessage,
    PreparedTaskSubmitMessage,
    SuccessfulSubmitResult,
    TaskPollResult,
    TaskRunRecordUpdate,
    TaskSubmitMessage,
    UpdateRecordMessage,
    UpdateRecordResult,
    WorkflowRunGroupRecordUpdate,
    WorkflowRunRecordUpdate,
)
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.run_message import prepare_task
from pctasks.execute.template import (
    template_args,
    template_foreach,
    template_job_with_item,
)

logger = logging.getLogger(__name__)


MAX_POLLS = 10000
DEFAULT_WAIT_SECONDS = 10
MAX_WAIT_RETRIES = 10
MAX_TASK_TIME = 60 * 60 * 24 * 7  # 1 week
POLL_INTERVAL = 60  # seconds
CHECK_OUTPUT_INTERVAL = 5  # seconds


class JobState(PCBaseModel):
    job_submit_message: JobSubmitMessage
    task_outputs: Dict[str, Any] = {}
    current_task: Optional[PreparedTaskSubmitMessage]
    current_submit_result: Optional[Union[SuccessfulSubmitResult, FailedSubmitResult]]
    task_queue: List[TaskConfig]

    def prepare_next_task(self, settings: ExecutorSettings) -> None:
        next_task_config = next(iter(self.task_queue), None)
        if next_task_config:
            copied_task = next_task_config.__class__.parse_obj(next_task_config.dict())
            copied_task.args = template_args(
                copied_task.args,
                job_outputs=self.job_submit_message.job_outputs,
                task_outputs=self.task_outputs,
                trigger_event=None,
            )

            next_task_submit_message = TaskSubmitMessage(
                dataset=self.job_submit_message.dataset,
                run_id=self.job_submit_message.run_id,
                job_id=self.job_submit_message.job_id,
                tokens=self.job_submit_message.tokens,
                config=copied_task,
                target_environment=self.job_submit_message.target_environment,
                instance_id="TODO:REMOVE",
            )

            self.current_task = prepare_task(
                next_task_submit_message, self.job_submit_message.run_id, settings
            )
        else:
            self.current_task = None
        self.current_submit_result = None
        self.task_queue = self.task_queue[1:]

    def submit_current_task(
        self, executor: TaskExecutor, settings: ExecutorSettings
    ) -> None:
        if self.current_task:
            if self.current_submit_result:
                raise Exception(
                    f"Task {self.current_task.task_submit_message.config.id} "
                    "already submitted "
                    f"for job {self.job_submit_message.job_id}"
                )
            self.current_submit_result = executor.submit([self.current_task], settings)[
                0
            ]
        else:
            raise Exception("No task to submit")


class RemoteRunner:
    """Runs a workflow through executing tasks remotely via a task executor."""

    def __init__(self, executor_settings: Optional[ExecutorSettings] = None) -> None:
        self.executor_settings = executor_settings or ExecutorSettings.get()
        self.executor = get_executor(self.executor_settings)

    def update_record(
        self, msg: UpdateRecordMessage, run_logger: RunLogger
    ) -> UpdateRecordResult:
        settings = self.executor_settings
        update = msg.update

        try:

            # Workflow Run Group

            if isinstance(update, CreateWorkflowRunGroupRecordUpdate):
                run_logger.info("Creating workflow run group...")
                with settings.get_workflow_run_group_record_table() as wrg_table:
                    wrg_table.insert_record(update.record)
            elif isinstance(update, WorkflowRunGroupRecordUpdate):
                run_logger.info(
                    f"Updating workflow run group record status to {update.status}."
                )
                with settings.get_workflow_run_group_record_table() as wrg_table:
                    wrg_record = wrg_table.get_record(
                        dataset=update.dataset, group_id=update.group_id
                    )
                    if not wrg_record:
                        return UpdateRecordResult(
                            error="Record not found.",
                        )
                    wrg_record.set_update_time()
                    update.update_record(wrg_record)
                    wrg_table.update_record(wrg_record)

            # Workflow Run

            elif isinstance(update, CreateWorkflowRunRecordUpdate):
                run_logger.info("Creating workflow run ...")
                with settings.get_workflow_run_record_table() as wr_table:
                    wr_table.insert_record(update.record)
            elif isinstance(update, WorkflowRunRecordUpdate):
                run_logger.info(
                    f"Updating workflow run record status to {update.status}."
                )
                with settings.get_workflow_run_record_table() as wr_table:
                    wr_record = wr_table.get_record(update.get_run_record_id())
                    if not wr_record:
                        return UpdateRecordResult(error="Record not found.")
                    wr_record.set_update_time()
                    update.update_record(wr_record)
                    wr_table.update_record(wr_record)

            # Job Run

            elif isinstance(update, CreateJobRunRecordUpdate):
                run_logger.info("Creating job run ...")
                with settings.get_job_run_record_table() as jr_table:
                    jr_table.insert_record(update.record)
            elif isinstance(update, JobRunRecordUpdate):
                run_logger.info(f"Updating job run record status to {update.status}.")
                with settings.get_job_run_record_table() as jr_table:
                    jr_record = jr_table.get_record(update.get_run_record_id())
                    if not jr_record:
                        return UpdateRecordResult(error="Record not found.")
                    jr_record.set_update_time()
                    update.update_record(jr_record)
                    jr_table.update_record(jr_record)

            # Task Run

            elif isinstance(update, CreateTaskRunRecordUpdate):
                run_logger.info("Creating task run ...")
                with settings.get_task_run_record_table() as tr_table:
                    tr_table.insert_record(update.record)
            else:
                with settings.get_task_run_record_table() as tr_table:
                    run_logger.info(
                        f"Updating task run record status to {update.status}."
                    )
                    tr_record = tr_table.get_record(update.get_run_record_id())
                    if not tr_record:
                        return UpdateRecordResult(error="Record not found.")
                    tr_record.set_update_time()
                    update.update_record(tr_record)
                    tr_table.update_record(tr_record)

            return UpdateRecordResult()
        except Exception as e:
            return UpdateRecordResult(error=str(e))

    def check_for_output(
        self, submit_result: SuccessfulSubmitResult, storage: Storage
    ) -> Optional[TaskResult]:
        path = storage.get_path(submit_result.output_uri)

        if storage.file_exists(path):
            return TaskResult.parse_subclass(storage.read_json(path))
        else:
            return None

    def poll_task(
        self, executor_id: Dict[str, Any], poll_count: int, run_logger: RunLogger
    ) -> TaskPollResult:
        try:
            result = self.executor.poll_task(
                executor_id,
                previous_poll_count=poll_count,
                settings=self.executor_settings,
            )
            logger.debug(f"Polled task {json.dumps(executor_id)}: {result}")
            return result
        except Exception as e:
            run_logger.log_event(
                TaskRunStatus.FAILED, message=f"Failed to poll task: {e}"
            )
            error_lines = str(e).split("\n")

            return TaskPollResult(
                task_status=TaskRunStatus.FAILED,
                poll_errors=[f"Failed to poll task {json.dumps(executor_id)}"]
                + error_lines,
            )

    def watch_task(
        self,
        submit_result: SuccessfulSubmitResult,
        run_logger: RunLogger,
    ) -> TaskResult:
        """Poll task and signal queue and report task status on completion."""
        task_io_storage = self.executor_settings.get_task_io_storage()

        check_output_result: Optional[TaskResult] = None
        poll_count = 0

        start_time = time.monotonic()
        task_poll_result: TaskPollResult = self.poll_task(
            submit_result.executor_id, poll_count, run_logger
        )
        poll_count += 1
        last_poll_time = start_time

        check_output_result = self.check_for_output(submit_result, task_io_storage)
        last_signal_check = start_time

        while not (task_poll_result.is_finished or check_output_result):
            time.sleep(1)
            loop_time = time.monotonic()

            # Check for timeout
            if loop_time - start_time > MAX_TASK_TIME:
                break

            if loop_time - last_poll_time > POLL_INTERVAL:
                task_poll_result = self.poll_task(
                    submit_result.executor_id, poll_count, run_logger
                )
                poll_count += 1
                last_poll_time = loop_time

            if loop_time - last_signal_check > CHECK_OUTPUT_INTERVAL:
                check_output_result = self.check_for_output(
                    submit_result, task_io_storage
                )
                last_signal_check = loop_time

        if not check_output_result:
            # One last output check
            check_output_result = self.check_for_output(submit_result, task_io_storage)

        if check_output_result:
            return check_output_result
        else:
            # Task failed without producing output
            if task_poll_result.task_status == TaskRunStatus.COMPLETED:
                # If task completed successfully, output should have been written
                return FailedTaskResult(
                    errors=["Task completed, but no output was written."]
                )
            elif task_poll_result.task_status == TaskRunStatus.FAILED:
                return FailedTaskResult(
                    errors=["The task status was marked as failed by the executor."]
                )
            else:
                # Fail due to timeout
                return FailedTaskResult(errors=["The task timed out."])

    def create_job_state(self, job_submit_message: JobSubmitMessage) -> JobState:
        job_state = JobState(
            job_submit_message=job_submit_message,
            current_task=None,
            current_submit_result=None,
            task_queue=job_submit_message.job.tasks[:],
        )
        job_state.prepare_next_task(self.executor_settings)
        return job_state

    def complete_job(
        self, job_state: JobState, run_logger: RunLogger
    ) -> Dict[str, Any]:
        run_id = job_state.job_submit_message.run_id
        job_id = job_state.job_submit_message.job_id
        while job_state.current_task:
            current_task_id = job_state.current_task.task_submit_message.config.id
            current_submit_result = job_state.current_submit_result

            if not current_submit_result:
                raise Exception("Incorrect state: no submit result")

            if isinstance(current_submit_result, FailedSubmitResult):
                # Update task as failed
                # Update job as failed
                # raise exception
                raise Exception()

            task_result = self.watch_task(current_submit_result, run_logger)

            wait_retries = 0

            if isinstance(task_result, WaitTaskResult):
                # If this is a WaitTaskResult, and it's not exceeding
                # the max retries, we wait for the given time and then
                # replay the orchestrator as a new flow.

                wait_retries += 1
                if wait_retries > MAX_WAIT_RETRIES:
                    raise Exception(f"Task timed out after {MAX_WAIT_RETRIES} tries.")

                current_wait_seconds = task_result.wait_seconds or DEFAULT_WAIT_SECONDS

                self.update_record(
                    UpdateRecordMessage(
                        update=TaskRunRecordUpdate(
                            status=TaskRunStatus.WAITING,
                            run_id=run_id,
                            job_id=job_id,
                            task_id=current_task_id,
                        )
                    ),
                    run_logger,
                )

                time.sleep(current_wait_seconds)

                self.update_record(
                    UpdateRecordMessage(
                        update=TaskRunRecordUpdate(
                            status=TaskRunStatus.SUBMITTED,
                            run_id=run_id,
                            job_id=job_id,
                            task_id=current_task_id,
                        )
                    ),
                    run_logger,
                )

                # Resubmit the task.
                job_state.current_submit_result = self.executor.submit(
                    [job_state.current_task], settings=self.executor_settings
                )[0]
            else:
                if isinstance(task_result, CompletedTaskResult):
                    job_state.task_outputs[
                        job_state.current_task.task_submit_message.config.id
                    ] = {"output": task_result.output}
                elif isinstance(task_result, FailedTaskResult):
                    raise TaskFailedError(
                        "Task failed: "
                        f"{','.join(task_result.errors or ['Task errored.'])}"
                    )
                elif isinstance(task_result, WaitTaskResult):
                    raise TaskFailedError(
                        f"Task responded with WaitTaskResult: {task_result.message}"
                    )
                else:
                    raise TaskFailedError(f"Unknown task result: {task_result}")

                job_state.prepare_next_task(self.executor_settings)
                job_state.submit_current_task(self.executor, self.executor_settings)

        return job_state.task_outputs

    def run_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:
        """Runs a workflow through executing tasks in Azure Batch."""

        pool = futures.ThreadPoolExecutor()

        workflow = submit_message.get_workflow_with_templated_args()
        run_record_id = submit_message.get_run_record_id()
        run_logger = RunLogger(run_record_id, logger_id="RUNNER")
        trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)

        run_logger.info(f"Running workflow: {workflow.name} run id {run_record_id}")
        logger.info("***********************************")
        logger.info(f"Workflow: {submit_message.workflow.name}")
        logger.info(f"Run Id: {submit_message.run_id}")
        logger.info("***********************************")

        # TODO: Create RECEIVED record in Azure Function

        workflow_run_record = WorkflowRunRecord(
            dataset=submit_message.workflow.get_dataset_id(),
            run_id=submit_message.run_id,
            workflow=submit_message.workflow,
            trigger_event=submit_message.trigger_event,
            args=submit_message.args,
            status=WorkflowRunStatus.RUNNING,
        )

        self.update_record(
            UpdateRecordMessage(
                update=CreateWorkflowRunRecordUpdate(
                    record=workflow_run_record,
                )
            ),
            run_logger=run_logger,
        )

        job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}

        workflow_jobs = list(workflow.jobs.values())
        sorted_jobs = sort_jobs(workflow_jobs)
        logger.info(f"Running jobs: {[j.id for j in sorted_jobs]}")
        for base_job in sorted_jobs:
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
                msg = f" - Running {len(jobs)} jobs in parallel"
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

            # Prepare tasks
            job_states = pool.map(self.create_job_state, job_submit_messages)
            initial_tasks: List[PreparedTaskSubmitMessage] = []
            for job_state in job_states:
                if not job_state.current_task:
                    raise Exception(
                        f"Job {job_state.job_submit_message.job.id} has no tasks."
                    )
                initial_tasks.append(job_state.current_task)

            # First tasks in a job are submitted in bulk to minimize
            # the number of concurrent API calls.
            submit_results = self.executor.submit(
                initial_tasks, settings=self.executor_settings
            )

            for job_state, submit_result in zip(job_states, submit_results):
                job_state.current_submit_result = submit_result

            # Wait for the first task of the job to complete, and then complete
            # all remaining tasks

            job_futures = {
                pool.submit(self.complete_job, job_state, run_logger): job_state
                for job_state in job_states
            }

            job_results: List[Dict[str, Any]] = []

            job_done_count = 0
            for job_future in futures.as_completed(job_futures.keys()):
                job_state = job_futures[job_future]

                # TODO: Future error handling
                future_error = job_future.exception()
                if future_error:
                    logger.info(
                        f"Job {job_state.job_submit_message.job_id} "
                        f"failed: {future_error}"
                    )
                    raise future_error

                if job_future.cancelled():
                    raise Exception("Job was cancelled.")

                job_done_count += 1
                logger.info(
                    f" -- Job {job_state.job_submit_message.job_id} completed. "
                    f"({job_done_count}/{total_job_count})"
                )
                job_results.append(job_future.result())

            if len(job_results) == 1:
                job_outputs[base_job.get_id()] = {TASKS_TEMPLATE_PATH: job_results[0]}
            else:
                job_output_entry: List[Dict[str, Any]] = []
                for job_result in job_results:
                    job_output_entry.append({TASKS_TEMPLATE_PATH: job_result})
                job_outputs[base_job.get_id()] = job_output_entry

            run_logger.log_event(
                status=JobRunStatus.COMPLETED,
                message=f"Job group {base_job.id} completed.",
            )

        logger.info("Workflow completed.")

        return job_outputs

    # TODO: Remove, deprecated

    def run_task(
        self, submit_message: TaskSubmitMessage, run_logger: Optional[RunLogger] = None
    ) -> TaskResult:
        """Runs a task in a local setting, without communicating with the executor.

        Useful for running tasks locally without going through the submit process.
        """

        run_record_id = submit_message.get_run_record_id()
        run_id = run_record_id.run_id
        job_id = submit_message.job_id
        task_id = submit_message.config.id

        run_logger = run_logger or RunLogger(
            run_record_id=run_record_id, logger_id="TASK"
        )

        self.update_record(
            UpdateRecordMessage(
                update=CreateTaskRunRecordUpdate(
                    record=TaskRunRecord(
                        status=TaskRunStatus.SUBMITTING,
                        run_id=run_id,
                        job_id=job_id,
                        task_id=task_id,
                    )
                )
            ),
            run_logger,
        )

        task_completed = False

        while not task_completed:

            try:

                # Submit the task.

                try:
                    logger.info(f"Submitting task {job_id}/{task_id}.")
                    submit_result = self.executor.submit(
                        submit_message, run_logger
                    ).result
                except Exception as e:
                    logger.exception(e)
                    raise TaskFailedError(e) from e  # TODO

                if isinstance(submit_result, FailedSubmitResult):
                    return FailedTaskResult(
                        errors=["Failed to submit task."] + submit_result.errors
                    )
                else:
                    logger.info(f"Submitting task {job_id}/{task_id}.")

                    self.update_record(
                        UpdateRecordMessage(
                            update=TaskRunRecordUpdate(
                                status=TaskRunStatus.SUBMITTED,
                                run_id=run_id,
                                job_id=job_id,
                                task_id=task_id,
                            )
                        ),
                        run_logger,
                    )

                task_result = self.watch_task(submit_result, run_logger)

                logger.info(f"Task {job_id}/{task_id} returned.")

                if isinstance(task_result, WaitTaskResult):
                    # If this is a WaitTaskResult, and it's not exceeding
                    # the max retries, we wait for the given time and then
                    # replay the orchestrator as a new flow.

                    submit_message.wait_retries += 1
                    if submit_message.wait_retries > MAX_WAIT_RETRIES:
                        return FailedTaskResult(
                            errors=[f"Task timed out after {MAX_WAIT_RETRIES} tries."]
                        )

                    current_wait_seconds = (
                        task_result.wait_seconds or DEFAULT_WAIT_SECONDS
                    )

                    self.update_record(
                        UpdateRecordMessage(
                            update=TaskRunRecordUpdate(
                                status=TaskRunStatus.WAITING,
                                run_id=run_id,
                                job_id=job_id,
                                task_id=task_id,
                            )
                        ),
                        run_logger,
                    )

                    time.sleep(current_wait_seconds)

                    self.update_record(
                        UpdateRecordMessage(
                            update=TaskRunRecordUpdate(
                                status=TaskRunStatus.SUBMITTED,
                                run_id=run_id,
                                job_id=job_id,
                                task_id=task_id,
                            )
                        ),
                        run_logger,
                    )
                else:
                    return task_result

            except Exception as e:
                logger.exception(e)
                run_logger.log_event(TaskRunStatus.FAILED, message=str(e))
                raise
                # return FailedTaskResult(errors=[str(e)])

        # Should return above
        return FailedTaskResult(
            errors=["Unexpected error occurred while running task."]
        )

    def run_job(
        self, submit_message: JobSubmitMessage, run_logger: RunLogger
    ) -> Dict[str, Any]:
        """Runs a job and returns the final task result."""

        task_outputs: Dict[str, Any] = {}

        job = submit_message.job
        job_id = job.get_id()

        logger.info(f"Running job {job_id}...")

        for task_config in job.tasks:
            copied_task = task_config.__class__.parse_obj(task_config.dict())
            copied_task.args = template_args(
                copied_task.args,
                job_outputs=submit_message.job_outputs,
                task_outputs=task_outputs,
                trigger_event=None,
            )

            task_submit_msg = TaskSubmitMessage(
                dataset=submit_message.dataset,
                run_id=submit_message.run_id,
                job_id=job_id,
                tokens=submit_message.tokens,
                config=copied_task,
                target_environment=submit_message.target_environment,
                instance_id="TODO:REMOVE",
            )

            task_result = self.run_task(task_submit_msg, run_logger)

            if isinstance(task_result, CompletedTaskResult):
                task_outputs[task_config.id] = {"output": task_result.output}
            elif isinstance(task_result, FailedTaskResult):
                raise TaskFailedError(
                    f"Task failed: {','.join(task_result.errors or ['Task errored.'])}"
                )
            elif isinstance(task_result, WaitTaskResult):
                raise TaskFailedError(
                    f"Task responded with WaitTaskResult: {task_result.message}"
                )
            else:
                raise TaskFailedError(f"Unknown task result: {task_result}")

        logger.info(f"Job {job_id} complete!")

        return task_outputs
