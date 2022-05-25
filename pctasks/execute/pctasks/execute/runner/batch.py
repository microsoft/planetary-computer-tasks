from datetime import timedelta
import logging
import os
from importlib.metadata import EntryPoint
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pctasks.core.logging import RunLogger
from pctasks.core.models.record import (
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)

from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskConfig,
    TaskResult,
    TaskResultType,
    WaitTaskResult,
)
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.core.storage import StorageFactory
from pctasks.core.utils import environment, map_opt
from pctasks.execute.constants import TASKS_TEMPLATE_PATH
from pctasks.execute.dag import sort_jobs
from pctasks.execute.errors import TaskFailedError
from pctasks.execute.models import (
    CreateWorkflowRunRecordUpdate,
    FailedSubmitResult,
    HandleTaskResultMessage,
    HandledTaskResult,
    JobSubmitMessage,
    SuccessfulSubmitResult,
    TaskPollMessage,
    TaskPollResult,
    TaskSubmitMessage,
    TaskSubmitResult,
    UpdateRecordMessage,
)
from pctasks.execute.secrets.local import LocalSecretsProvider
from pctasks.execute.task.activities import handle_result, poll, submit, update_record
from pctasks.execute.task.submit import submit_task
from pctasks.execute.template import (
    template_args,
    template_foreach,
    template_job_with_item,
)
from pctasks.task.context import TaskContext
from pctasks.task.run import MissingEnvironmentError, TaskLoadError
from pctasks.task.task import Task

from pctasks_funcs.TaskOrch import WaitTimeoutError

logger = logging.getLogger(__name__)


MAX_POLLS = 10000
DEFAULT_WAIT_SECONDS = 10
MAX_WAIT_RETRIES = 10


class BatchRunner:
    def poll_task(self, poll_msg: TaskPollMessage, run_logger: RunLogger) -> TaskPollResult:
        # A task will signal that it is completed.
        # Allow this to interrupt the polling timer.

        for _ in range(0, MAX_POLLS):
            # TODO: Poll message queue
            task_poll_result = poll(poll_msg, run_logger)

            if (
                task_poll_result.task_status == TaskRunStatus.COMPLETED
                or task_poll_result.task_status == TaskRunStatus.FAILED
            ):
                return task_poll_result.json()
            else:

                # TERMINATE METHOD
                expiration = context.current_utc_datetime + timedelta(seconds=10)
                timer = context.create_timer(expiration)

                try:
                    winner = yield context.task_any([signal_event, timer])
                except Exception as e:
                    logger.exception(e)
                    raise PollFailedError(
                        "Failed while wait for task signal or poll: "
                        f"{parse_activity_exception(e)}"
                    ) from e

                if winner == signal_event:
                    if not timer.is_completed:
                        cast(TimerTask, timer).cancel()

                    # The task has signaled its completion or failure.
                    signal_msg = TaskRunSignal.parse_raw(signal_event.result)

                    # Ensure the signal key from the submit result matches,
                    # to ensure the signal origin is known.
                    if signal_msg.signal_key != poll_msg.signal_key:
                        raise PollFailedError(
                            f"Signal key mismatch: {signal_msg.signal_key} "
                            f"vs submitted: {poll_msg.signal_key}"
                        )

                    if signal_msg.task_result_type == TaskResultType.COMPLETED:
                        return TaskPollResult(task_status=TaskRunStatus.COMPLETED).json()
                    else:
                        return TaskPollResult(task_status=TaskRunStatus.FAILED).json()

                poll_msg.previous_poll_count += 1

                # # Check parent status.
                # parent_status = yield context.call_activity(
                #     ActivityNames.ORCH_FETCH_STATUS, input_=poll_msg.parent_instance_id
                # )
                # if (
                #     df.OrchestrationRuntimeStatus(parent_status)
                #     != df.OrchestrationRuntimeStatus.Running
                # ):
                #     if not context.is_replaying:
                #         logger.warn(f"Canceling poll task as parent is {parent_status}")
                #     return TaskPollResult(task_status=TaskRunStatus.CANCELLED).json()

                # ## SIGNAL METHOD

                # # Wait to poll again, or for the signal to quit.
                # signal_event = context.wait_for_external_event(EventNames.POLL_QUIT)
                # timer = context.create_timer(
                #     context.current_utc_datetime + timedelta(seconds=30)
                # )

                # try:
                #     winner = yield context.task_any([signal_event, timer])
                # except Exception as e:
                #     logger.exception(e)
                #     raise PollFailedError("Failed while wait for task signal or poll") from e

                # if winner == signal_event:
                #     logger.info("Polling stopped by signal.")
                #     if not timer.is_completed:
                #         logger.info(" - Cancelling timer!")
                #         cast(TimerTask, timer).cancel()

                #     return TaskPollResult(task_status=TaskRunStatus.CANCELLED).json()
                # else:

                #     # Check parent status.
                #     parent_status = yield context.call_activity(
                #         ActivityNames.ORCH_FETCH_STATUS, input_=poll_msg.parent_instance_id
                #     )
                #     if (
                #         df.OrchestrationRuntimeStatus(parent_status)
                #         != df.OrchestrationRuntimeStatus.Running
                #     ):
                #         if not context.is_replaying:
                #             logger.warn(f"Canceling poll task as parent is {parent_status}")
                #         return TaskPollResult(task_status=TaskRunStatus.CANCELLED).json()

                #     poll_msg.previous_poll_count += 1
                #     context.continue_as_new(poll_msg.json())
        return TaskPollResult(
            task_status=TaskRunStatus.FAILED,
            poll_errors=[f"Exceeded max polls ({MAX_POLLS})."],
        ).json()

    def run_task(
        self, submit_message: TaskSubmitMessage, run_logger: Optional[RunLogger] = None
    ) -> TaskResult:
        """Runs a task in a local setting, without communicating with the executor.

        Useful for running tasks locally without going through the submit process.
        """

        instance_id = uuid4().hex

        run_record_id = submit_message.get_run_record_id()
        run_id = run_record_id.run_id
        job_id = submit_message.job_id
        task_id = submit_message.config.id

        run_logger = run_logger or RunLogger(
            run_record_id=run_record_id, logger_id="TASK"
        )

        # TODO: UPDATE RECORD

        errors: Optional[List[str]] = None
        handled_result: Optional[HandledTaskResult] = None

        try:

            # Submit the task.

            try:
                submit_result = submit(submit_message, run_logger).result
            except Exception as e:
                logger.exception(e)
                raise TaskFailedError(e) from e  # TODO

            if isinstance(submit_result, FailedSubmitResult):
                errors = (errors or []) + submit_result.errors

                raise TaskFailedError(f"Failed to sumbit task {task_id}")
            else:
                run_logger.info("Submitted task!")

                # TODO: UPDATE TASK SUBMITTED

            # # The signal event is pushed by the task
            # signal_event = context.wait_for_external_event(EventNames.TASK_SIGNAL)

            # Also poll the executor for the task status in case
            # of early failure.
            # poll_orch_id = context.new_guid().hex

            # -- POLL

            poll_result = self.poll_task()

            if poll_result.poll_errors:
                errors = (errors or []) + poll_result.poll_errors

            if poll_result.task_status == TaskRunStatus.COMPLETED:
                task_result_type = TaskResultType.COMPLETED
            else:
                task_result_type = TaskResultType.FAILED

            # Handle the task result and pass back any output.

            handled_result = handle_result(
                HandleTaskResultMessage(
                    task_result_type=task_result_type,
                    submit_result=submit_result,
                    run_record_id=run_record_id,
                    target_environment=submit_message.target_environment,
                    log_uri=submit_result.log_uri,
                    errors=errors,
                ),
                event_logger=run_logger,
            )

            if isinstance(handled_result, WaitTaskResult):
                # If this is a WaitTaskResult, and it's not exceeding
                # the max retries, we wait for the given time and then
                # replay the orchestrator as a new flow.

                submit_message.wait_retries += 1
                if submit_message.wait_retries > MAX_WAIT_RETRIES:
                    # TODO: Handle max tries exceeded
                    raise WaitTimeoutError(
                        f"Task timed out after {MAX_WAIT_RETRIES} tries."
                    )

                delta = timedelta(
                    seconds=(handled_result.wait_seconds or DEFAULT_WAIT_SECONDS)
                )

                # TODO: Update task record to WAITING

                # TODO: Wait

                # TODO: Update to SUBMITTING

        except Exception as e:
            logger.exception(e)
            run_logger.log_event(TaskRunStatus.FAILED, message=str(e))
            errors = (errors or []) + [str(e)]

        # if poll_orch_id:
        #     yield context.call_activity(ActivityNames.ORCH_CANCEL, input_=poll_orch_id)

        if errors:
            return HandledTaskResult(result=FailedTaskResult(errors=errors)).json()
        else:
            if not handled_result:
                return HandledTaskResult(
                    result=FailedTaskResult(
                        errors=(errors or []) + ["No result returned"]
                    )
                ).json()
            else:
                return handled_result.json()

    def run_job(
        self, submit_message: JobSubmitMessage, run_logger: Optional[RunLogger] = None
    ) -> Dict[str, Any]:
        """Runs a job and returns the final task result."""
        run_record_id = submit_message.get_run_record_id()
        run_logger = run_logger or RunLogger(
            run_record_id=run_record_id, logger_id="JOB"
        )

        task_outputs: Dict[str, Any] = {}

        job = submit_message.job
        job_id = job.get_id()

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
                instance_id=None,
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

        return task_outputs

    def run_workflow(
        self,
        submit_message: WorkflowSubmitMessage,
    ) -> Dict[str, Any]:
        """Runs a workflow through executing tasks in Azure Batch."""

        workflow = submit_message.get_workflow_with_templated_args()
        run_record_id = submit_message.get_run_record_id()
        run_logger = RunLogger(run_record_id, logger_id="WORKFLOW")
        trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)

        # TODO: Create RECEIVED record in Azure Function
        workflow_run_record = WorkflowRunRecord(
            dataset=submit_message.workflow.get_dataset_id(),
            run_id=submit_message.run_id,
            workflow=submit_message.workflow,
            trigger_event=submit_message.trigger_event,
            args=submit_message.args,
            status=WorkflowRunStatus.RUNNING,
        )

        update_record(
            UpdateRecordMessage(
                update=CreateWorkflowRunRecordUpdate(
                    record=workflow_run_record,
                )
            ),
            event_logger=run_logger,
        )

        job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}

        workflow_jobs = list(workflow.jobs.values())
        sorted_jobs = sort_jobs(workflow_jobs)
        for base_job in sorted_jobs:

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
            else:
                jobs = [base_job]

            job_results: List[Dict[str, Any]] = []
            for prepared_job in jobs:
                job_submit_message = JobSubmitMessage(
                    job=prepared_job,
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    job_id=prepared_job.get_id(),
                    tokens=workflow.tokens,
                    target_environment=workflow.target_environment,
                    job_outputs=job_outputs,
                    trigger_event=trigger_event,
                )
                job_result = self.run_job(job_submit_message, run_logger)

                job_results.append(job_result)

            if len(job_results) == 1:
                job_outputs[base_job.get_id()] = {TASKS_TEMPLATE_PATH: job_results[0]}
            else:
                job_output_entry: List[Dict[str, Any]] = []
                for job_result in job_results:
                    job_output_entry.append({TASKS_TEMPLATE_PATH: job_result})
                job_outputs[base_job.get_id()] = job_output_entry

        return job_outputs
