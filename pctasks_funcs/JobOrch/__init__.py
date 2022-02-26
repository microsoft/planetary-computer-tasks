import logging
from typing import Any, Dict, Generator, List, Optional

import azure.durable_functions as df
from func_lib.activities import call_activity
from func_lib.flows.update_record import UpdateRecordOrchFlow

from pctasks.core.logging import RunLogger
from pctasks.core.models.record import JobRunStatus, TaskRunRecord, TaskRunStatus
from pctasks.core.models.task import FailedTaskResult
from pctasks.execute.constants import ActivityNames, OrchestratorNames
from pctasks.execute.models import (
    CompletedTaskResult,
    CreateTaskRunRecordUpdate,
    HandledTaskResult,
    JobResultMessage,
    JobRunRecordUpdate,
    JobSubmitMessage,
    NotificationSubmitResult,
    TaskRunRecordUpdate,
    TaskSubmitMessage,
    UpdateRecordMessage,
)
from pctasks.execute.template import template_args, template_notification

logger = logging.getLogger(__name__)


class JobFailedError(Exception):
    pass


def orchestrator(context: df.DurableOrchestrationContext) -> Generator[Any, Any, str]:
    msg = context.get_input()
    assert msg
    submit_message = JobSubmitMessage.parse_raw(msg)
    run_record_id = submit_message.get_run_record_id()
    event_logger = RunLogger(
        run_record_id=run_record_id, logger_id=OrchestratorNames.JOB
    )

    job = submit_message.job
    job_id = job.get_id()

    is_errored = False

    update_record_flow = UpdateRecordOrchFlow(
        context,
        event_logger,
        run_record_id=run_record_id,
    )

    ####################
    # Begin processing #
    ####################

    task_outputs: Dict[str, Dict[str, Any]] = {}
    errors: Optional[List[str]] = None

    # Update job to running.
    try:
        result = yield update_record_flow.create_task(
            update=JobRunRecordUpdate(
                run_id=submit_message.run_id, job_id=job_id, status=JobRunStatus.RUNNING
            ),
        )
        update_record_result = update_record_flow.handle_result(result, run_record_id)
        if update_record_result.error:
            raise JobFailedError(update_record_result.error)
    except Exception as e:
        update_record_flow.handle_error(e)
        errors = (errors or []) + [str(e)]
        is_errored = True

    handled_task_result: Optional[HandledTaskResult] = None
    task_errors: List[str] = []

    try:

        # Process each task in the job
        for task in job.tasks:

            # Set the task status to running.
            try:
                result = yield update_record_flow.create_task(
                    update=CreateTaskRunRecordUpdate(
                        record=TaskRunRecord(
                            status=TaskRunStatus.SUBMITTING
                            if not is_errored
                            else TaskRunStatus.CANCELLED,
                            run_id=submit_message.run_id,
                            job_id=job_id,
                            task_id=task.id,
                        )
                    ),
                )
                update_record_result = update_record_flow.handle_result(
                    result, run_record_id
                )
                if update_record_result.error:
                    raise JobFailedError(update_record_result.error)
            except Exception as e:
                update_record_flow.handle_error(e)
                errors = (errors or []) + [f"Failed to create task record: {e}"]
                is_errored = True

            if is_errored:
                continue

            #
            # Create the submit message
            #

            task_submit_msg = TaskSubmitMessage(
                dataset=submit_message.dataset,
                run_id=submit_message.run_id,
                job_id=job_id,
                tokens=submit_message.tokens,
                config=task,
                target_environment=submit_message.target_environment,
                instance_id=None,
            )

            # Populate templated values in the task arguments
            # with trigger event and previous job and task outputs.
            task_submit_msg.config.args = template_args(
                task_submit_msg.config.args,
                job_outputs=submit_message.job_outputs,
                task_outputs=task_outputs,
                trigger_event=submit_message.trigger_event,
            )

            if not context.is_replaying:
                event_logger.info(
                    f"Submitting task: {task_submit_msg.get_run_record_id()}"
                )

            #
            # Submit the task
            #

            try:
                handled_task_result_str = yield context.call_sub_orchestrator(
                    OrchestratorNames.TASK,
                    input_=task_submit_msg.json(),
                    instance_id=context.new_guid().hex,
                )
                handled_task_result = HandledTaskResult.parse_raw(
                    handled_task_result_str
                )
            except Exception as e:
                if not context.is_replaying:
                    logger.exception(e)
                    event_logger.log_event(
                        JobRunStatus.FAILED, properties={"error": str(e)}
                    )
                is_errored = True
                task_errors.extend(["Task orchestrator failed", str(e)])

            #
            # Handle result
            #

            # if not context.is_replaying:
            #     event_logger.info(f"Task result: {handled_task_result}.")

            if not is_errored and handled_task_result:

                if isinstance(handled_task_result.result, CompletedTaskResult):
                    output = handled_task_result.result.output
                    if output:
                        task_outputs[task.id] = output

                    # Task completed successfully
                    yield call_activity(
                        context,
                        name=ActivityNames.UPDATE_RECORD,
                        msg=UpdateRecordMessage(
                            update=TaskRunRecordUpdate(
                                status=TaskRunStatus.COMPLETED,
                                run_id=submit_message.run_id,
                                job_id=job_id,
                                task_id=task.id,
                                log_uris=handled_task_result.log_uris,
                            ),
                        ),
                        run_record_id=run_record_id,
                        job_id=job_id,
                        task_id=task.id,
                    )
                else:
                    is_errored = True

                    if isinstance(handled_task_result.result, FailedTaskResult):
                        task_errors.extend(
                            ["Task failed"] + (handled_task_result.result.errors or [])
                        )

                    else:
                        task_errors.extend(
                            ["Task failed to meet criteria in the required time."]
                            + [str(handled_task_result.result)]
                        )

                    errors = (errors or []) + [
                        f"Task {task.id} failed. See task for details."
                    ]

            if is_errored:
                error_update = TaskRunRecordUpdate(
                    status=TaskRunStatus.FAILED,
                    run_id=submit_message.run_id,
                    job_id=job_id,
                    task_id=task.id,
                    errors=task_errors,
                    log_uris=handled_task_result.log_uris
                    if handled_task_result
                    else None,
                )

                yield call_activity(
                    context,
                    name=ActivityNames.UPDATE_RECORD,
                    msg=UpdateRecordMessage(update=error_update),
                    run_record_id=run_record_id,
                    job_id=job_id,
                    task_id=task.id,
                )

            # --------------------
            # Done processing task
    except Exception as e:
        is_errored = True
        errors = (errors or []) + [f"Failure during task processing: {e}"]

    # -------------------
    # Done processing all tasks

    if not is_errored:
        # Handle notifications
        if job.notifications:
            for notification in job.notifications:
                templated_notification = template_notification(
                    notification=notification, task_outputs=task_outputs
                )
                notification_message = templated_notification.to_message()
                send_notification_result_str = yield call_activity(
                    context,
                    name=ActivityNames.JOB_SEND_NOTIFICATION,
                    msg=notification_message,
                    run_record_id=run_record_id,
                    job_id=job_id,
                )
                send_notification_result = NotificationSubmitResult.parse_raw(
                    send_notification_result_str
                )
                if send_notification_result.error:
                    is_errored = True
                    errors = (errors or []) + [send_notification_result.error]

    if not is_errored:
        try:
            result = yield update_record_flow.create_task(
                update=JobRunRecordUpdate(
                    run_id=submit_message.run_id,
                    job_id=job_id,
                    status=JobRunStatus.COMPLETED,
                    errors=errors,
                ),
            )
            update_record_result = update_record_flow.handle_result(
                result, run_record_id
            )
            if update_record_result.error:
                raise JobFailedError(update_record_result.error)
        except Exception as e:
            update_record_flow.handle_error(e)
            errors = (errors or []) + [str(e)]
            is_errored = True

    if is_errored:
        try:
            result = yield update_record_flow.create_task(
                update=JobRunRecordUpdate(
                    run_id=submit_message.run_id,
                    job_id=job_id,
                    status=JobRunStatus.FAILED,
                    errors=errors,
                ),
            )
            update_record_result = update_record_flow.handle_result(
                result, run_record_id
            )
            if update_record_result.error:
                raise JobFailedError(update_record_result.error)
        except Exception as e:
            update_record_flow.handle_error(e)
            errors = (errors or []) + [str(e)]
            is_errored = True

    if not context.is_replaying:
        if is_errored:
            event_logger.info(f"Job failed: {errors}.")
        else:
            event_logger.info("Job complete.")

    return JobResultMessage(
        job_id=job_id, task_outputs=task_outputs, errors=errors
    ).json()


main = df.Orchestrator.create(orchestrator)
