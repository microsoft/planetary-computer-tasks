import logging
from datetime import timedelta
from typing import Any, Optional

import azure.durable_functions as df
from func_lib.activities import call_activity, parse_activity_exception

from pctasks.core.models.record import TaskRunStatus
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import TaskPollMessage, TaskPollResult

logger = logging.getLogger(__name__)


def orchestrator(context: df.DurableOrchestrationContext) -> Any:
    msg_str: Optional[str] = context.get_input()
    if not msg_str:
        return TaskPollResult(
            task_status=TaskRunStatus.FAILED, poll_errors=["No message input received."]
        ).json()

    poll_msg = TaskPollMessage.parse_raw(msg_str)

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

    # logger.info(f"task_poll_result: {task_poll_result.json(indent=2)}")

    if (
        task_poll_result.task_status == TaskRunStatus.COMPLETED
        or task_poll_result.task_status == TaskRunStatus.FAILED
    ):
        # Wait 10 seconds in case the task signal is delayed.
        yield context.create_timer(context.current_utc_datetime + timedelta(seconds=10))

        return task_poll_result.json()
    else:
        yield context.create_timer(context.current_utc_datetime + timedelta(seconds=30))

        # Check parent status.
        parent_status = yield context.call_activity(
            ActivityNames.ORCH_FETCH_STATUS, input_=poll_msg.parent_instance_id
        )
        if (
            df.OrchestrationRuntimeStatus(parent_status)
            != df.OrchestrationRuntimeStatus.Running
        ):
            if not context.is_replaying:
                logger.warn(f"Canceling poll task as parent is {parent_status}")
            return TaskPollResult(task_status=TaskRunStatus.COMPLETED).json()

    poll_msg.previous_poll_count += 1
    context.continue_as_new(poll_msg.json())


main = df.Orchestrator.create(orchestrator)
