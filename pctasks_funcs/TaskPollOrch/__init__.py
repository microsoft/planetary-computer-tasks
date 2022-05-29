import logging
from datetime import timedelta
from typing import Any, Optional, cast

import azure.durable_functions as df
from azure.durable_functions.models.Task import TimerTask
from func_lib.activities import call_activity, parse_activity_exception

from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import TaskResultType, TaskRunSignal
from pctasks.execute.constants import ActivityNames, EventNames
from pctasks.execute.models import TaskPollMessage, TaskPollResult

logger = logging.getLogger(__name__)


MAX_POLLS = 10000


class PollFailedError(Exception):
    pass


def orchestrator(context: df.DurableOrchestrationContext) -> Any:
    msg_str: Optional[str] = context.get_input()
    if not msg_str:
        return TaskPollResult(
            task_status=TaskRunStatus.FAILED, poll_errors=["No message input received."]
        ).json()

    poll_msg = TaskPollMessage.parse_raw(msg_str)

    # A task will signal that it is completed.
    # Allow this to interrupt the polling timer.
    signal_event = context.wait_for_external_event(EventNames.TASK_SIGNAL)

    for _ in range(0, MAX_POLLS):
        try:
            result_str = yield call_activity(
                context,
                name=ActivityNames.TASK_POLL,
                msg=poll_msg,
                run_record_id=poll_msg.run_record_id,
            )
            task_poll_result = TaskPollResult.parse_raw(result_str)
        except Exception as e:
            logger.exception(e)
            msg = parse_activity_exception(e)
            return TaskPollResult(
                task_status=TaskRunStatus.FAILED, poll_errors=[msg]
            ).json()

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


main = df.Orchestrator.create(orchestrator)
