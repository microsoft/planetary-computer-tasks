import json
from typing import Optional, TypeVar

import azure.durable_functions as df
from azure.durable_functions.models.Task import TaskBase

from pctasks.core.models.activity import ActivityMessage
from pctasks.core.models.base import PCBaseModel, RunRecordId

T = TypeVar("T", bound=PCBaseModel)
U = TypeVar("U", bound=PCBaseModel)


def call_activity(
    context: df.DurableOrchestrationContext,
    name: str,
    msg: T,
    run_record_id: RunRecordId,
    job_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> TaskBase:
    activity_msg: ActivityMessage[T] = ActivityMessage(
        run_record_id=run_record_id.update(job_id=job_id, task_id=task_id), msg=msg
    )
    return context.call_activity(name, activity_msg.json())


def parse_activity_exception(e: Exception) -> str:
    """Attempt to parse out the relevant info from an activity exception.

    Defaults to calling str(e)
    """
    try:
        msg_text = str(e).split("\n")[1]
        js = json.loads(msg_text)
        return js["InnerException"]["Message"]
    except Exception:
        return str(e)
