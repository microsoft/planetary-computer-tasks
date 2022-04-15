"""Polls the executor for task status."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import UpdateRecordMessage
from pctasks.execute.task import activities


def event_tag(msg: UpdateRecordMessage) -> str:
    return msg.update.type


main = wrap_activity(
    activities.update_record,
    UpdateRecordMessage,
    ActivityNames.UPDATE_RECORD,
    event_tag=event_tag,
)
