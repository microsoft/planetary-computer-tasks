import logging
from datetime import timedelta
from typing import Any, Generator, List, Optional
from pydantic import ValidationError

import azure.durable_functions as df
from azure.durable_functions.models.Task import TaskBase
from func_lib.activities import call_activity, parse_activity_exception
from func_lib.flows.update_record import UpdateRecordOrchFlow
from func_lib.models import OrchSignal

from pctasks.core.logging import RunLogger
from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import (
    FailedTaskResult,
    TaskResultType,
    TaskRunSignal,
    WaitTaskResult,
)
from pctasks.execute.constants import ActivityNames, EventNames, OrchestratorNames
from pctasks.execute.models import (
    FailedSubmitResult,
    HandledTaskResult,
    HandleTaskResultMessage,
    TaskPollMessage,
    TaskPollResult,
    TaskRunRecordUpdate,
    TaskSubmitMessage,
    TaskSubmitResult,
)

DEFAULT_WAIT_SECONDS = 10
MAX_WAIT_RETRIES = 10

logger = logging.getLogger(__name__)


class WaitTimeoutError(Exception):
    pass


class TaskFailedError(Exception):
    pass


def orchestrator(
    context: df.DurableOrchestrationContext,
) -> Generator[TaskBase, Any, str]:
    submit_msg_str: Optional[str] = context.get_input()
    if not submit_msg_str:
        return HandledTaskResult(
            result=FailedTaskResult(errors=["No message received"])
        ).json()

    # Instance ID is passed along to task, so that
    # it can signal back to the orchestrator when
    # completed.
    instance_id = context.instance_id

    task_submit_msg = TaskSubmitMessage.parse_raw(submit_msg_str)

    run_record_id = task_submit_msg.get_run_record_id()
    run_id = run_record_id.run_id
    job_id = task_submit_msg.job_id
    task_id = task_submit_msg.config.id

    event_logger = RunLogger(
        run_record_id=run_record_id, logger_id=OrchestratorNames.TASK
    )

    update_record_flow = UpdateRecordOrchFlow(
        context,
        event_logger,
        run_record_id=run_record_id,
    )

    errors: Optional[List[str]] = None
    handled_result: Optional[HandledTaskResult] = None
    poll_orch_id: Optional[str] = None

    try:

        # Submit the task.

        poll_orch_id = context.new_guid().hex
        task_submit_msg.instance_id = poll_orch_id

        try:
            submit_result_str = yield call_activity(
                context,
                name=ActivityNames.TASK_SUBMIT,
                msg=task_submit_msg,
                run_record_id=run_record_id,
            )
            submit_result = TaskSubmitResult.parse_raw(submit_result_str).result
        except Exception as e:
            logger.exception(e)
            parsed_error = parse_activity_exception(e)
            raise TaskFailedError(parsed_error) from e

        # if not context.is_replaying:
        #     logger.warn(
        #         "\n\nINSTANCE ID FOR  "
        #         f"{task_submit_msg.job_id}/{task_submit_msg.config.id} "
        #         f"ORCHESTRATOR: {instance_id}\n\n"
        #     )

        if isinstance(submit_result, FailedSubmitResult):
            errors = (errors or []) + submit_result.errors

            raise TaskFailedError(f"Failed to sumbit task {task_id}")
        else:
            if not context.is_replaying:
                event_logger.info("Submitted task!")

            try:
                result = yield update_record_flow.create_task(
                    update=TaskRunRecordUpdate(
                        run_id=run_id,
                        job_id=job_id,
                        task_id=task_id,
                        status=TaskRunStatus.SUBMITTED,
                    ),
                )
                update_record_result = update_record_flow.handle_result(
                    result, run_record_id
                )
                if update_record_result.error:
                    raise TaskFailedError(update_record_result.error)
            except Exception as e:
                update_record_flow.handle_error(e)
                errors = (errors or []) + [str(e)]
                raise TaskFailedError(f"Failed to update record {run_record_id}") from e

        # # The signal event is pushed by the task
        # signal_event = context.wait_for_external_event(EventNames.TASK_SIGNAL)

        # Also poll the executor for the task status in case
        # of early failure.
        # poll_orch_id = context.new_guid().hex

        if not context.is_replaying:
            logger.info(f"Creating poll orchestrator {poll_orch_id}")
        poll_orch_result = yield context.call_sub_orchestrator(
            OrchestratorNames.TASK_POLL,
            input_=TaskPollMessage(
                executor_id=submit_result.executor_id,
                run_record_id=run_record_id,
                parent_instance_id=instance_id,
                signal_key=submit_result.signal_key,
            ).json(),
            instance_id=poll_orch_id,
        )
        # poll_orch = context.call_sub_orchestrator(
        #     OrchestratorNames.TASK_POLL,
        #     input_=TaskPollMessage(
        #         executor_id=submit_result.executor_id,
        #         run_record_id=run_record_id,
        #         parent_instance_id=instance_id,
        #         signal_key=submit_result.signal_key,
        #     ).json(),
        #     instance_id=poll_orch_id,
        # )

        # try:
        #     winner = yield context.task_any([signal_event, poll_orch])
        # except Exception as e:
        #     logger.exception(e)
        #     errors = (errors or []) + [parse_activity_exception(e)]
        #     raise TaskFailedError("Failed while wait for task signal or poll") from e

        # task_result_type: TaskResultType

        # if winner == signal_event:
        #     if not context.is_replaying:
        #         event_logger.info("Signal event raised!")

        #     # Cancel polling immediately
        #     # if poll_orch_id:

        #     #     # SIGNAL METHOD

        #     #     yield context.call_activity(
        #     #         ActivityNames.ORCH_CANCEL,
        #     #         input_=poll_orch_id
        #     #     )
        #     #     poll_orch_id = None

        #         # # SIGNAL METHOD

        #         # yield context.call_activity(
        #         #     ActivityNames.ORCH_SIGNAL,
        #         #     input_=OrchSignal(
        #         #         instance_id=poll_orch_id, event_name=EventNames.POLL_QUIT
        #         #     ).json(),
        #         # )
        #         # poll_orch_id = None

        #     # The task has signaled its completion or failure.
        #     signal_msg = TaskRunSignal.parse_raw(signal_event.result)

        #     # Ensure the signal key from the submit result matches,
        #     # to ensure the signal origin is known.
        #     if signal_msg.signal_key != submit_result.signal_key:
        #         raise TaskFailedError(
        #             f"Signal key mismatch: {signal_msg.signal_key} "
        #         )

        #     task_result_type = signal_msg.task_result_type

        # else:
        #     # Don't need to clean up the poll orchestrator.
        #     poll_orch_id = None

        #     # The task has completed or failed before a signal
        #     # was received. This normally means an early failure.
        #     if not context.is_replaying:
        #         event_logger.info("Task completed before signal!")
        try:
            poll_result = TaskPollResult.parse_raw(poll_orch_result)
        except ValidationError as e:
            logger.exception(e)
            event_logger.error(f"poll_orch_result: {poll_orch_result}")
            raise TaskFailedError(
                f"Failed to parse poll result: {poll_orch_result}\n{e}"
            ) from e

        if poll_result.poll_errors:
            errors = (errors or []) + poll_result.poll_errors

        if poll_result.task_status == TaskRunStatus.COMPLETED:
            task_result_type = TaskResultType.COMPLETED
        else:
            task_result_type = TaskResultType.FAILED

        # Handle the task result and pass back any output.

        handled_task_result_str = yield call_activity(
            context,
            name=ActivityNames.TASK_HANDLE_RESULT,
            msg=HandleTaskResultMessage(
                task_result_type=task_result_type,
                submit_result=submit_result,
                run_record_id=run_record_id,
                target_environment=task_submit_msg.target_environment,
                log_uri=submit_result.log_uri,
                errors=errors,
            ),
            run_record_id=run_record_id,
        )
        handled_result = HandledTaskResult.parse_raw(handled_task_result_str)

        if isinstance(handled_result, WaitTaskResult):
            # If this is a WaitTaskResult, and it's not exceeding
            # the max retries, we wait for the given time and then
            # replay the orchestrator as a new flow.

            task_submit_msg.wait_retries += 1
            if task_submit_msg.wait_retries > MAX_WAIT_RETRIES:
                # TODO: Handle max tries exceeded
                raise WaitTimeoutError(
                    f"Task timed out after {MAX_WAIT_RETRIES} tries."
                )

            delta = timedelta(
                seconds=(handled_result.wait_seconds or DEFAULT_WAIT_SECONDS)
            )

            # Update task record to WAITING
            try:
                result = yield update_record_flow.create_task(
                    update=TaskRunRecordUpdate(
                        run_id=run_id,
                        job_id=job_id,
                        task_id=task_id,
                        status=TaskRunStatus.WAITING,
                        log_uris=handled_result.log_uris,
                    ),
                )
                update_record_result = update_record_flow.handle_result(
                    result, run_record_id
                )
                if update_record_result.error:
                    raise TaskFailedError(update_record_result.error)
            except Exception as e:
                update_record_flow.handle_error(e)
                errors = (errors or []) + [str(e)]
                raise TaskFailedError(f"Failed to update record {run_record_id}") from e

            # Wait
            yield context.create_timer(context.current_utc_datetime + delta)

            # Update task record to SUBMITTING
            try:
                result = yield update_record_flow.create_task(
                    update=TaskRunRecordUpdate(
                        run_id=run_id,
                        job_id=job_id,
                        task_id=task_id,
                        status=TaskRunStatus.SUBMITTING,
                        log_uris=handled_result.log_uris,
                    ),
                )
                update_record_result = update_record_flow.handle_result(
                    result, run_record_id
                )
                if update_record_result.error:
                    raise TaskFailedError(update_record_result.error)

            except Exception as e:
                update_record_flow.handle_error(e)
                errors = (errors or []) + [str(e)]
                raise TaskFailedError(f"Failed to update record {run_record_id}")

            context.continue_as_new(task_submit_msg.json())

    except Exception as e:
        logger.exception(e)
        event_logger.log_event(TaskRunStatus.FAILED, message=str(e))
        errors = (errors or []) + [str(e)]

    # if poll_orch_id:
    #     yield context.call_activity(ActivityNames.ORCH_CANCEL, input_=poll_orch_id)

    if errors:
        return HandledTaskResult(result=FailedTaskResult(errors=errors)).json()
    else:
        if not handled_result:
            return HandledTaskResult(
                result=FailedTaskResult(errors=(errors or []) + ["No result returned"])
            ).json()
        else:
            return handled_result.json()


main = df.Orchestrator.create(orchestrator)
