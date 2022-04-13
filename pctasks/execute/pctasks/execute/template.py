from typing import Any, Dict, List, Optional, TypeVar

from pctasks.core.models.base import ForeachConfig
from pctasks.core.models.event import NotificationConfig
from pctasks.core.models.workflow import JobConfig
from pctasks.core.utils import completely_flatten
from pctasks.core.utils.template import (
    DictTemplater,
    TemplateError,
    Templater,
    TemplateValue,
    find_value,
    template_dict,
    template_str,
)
from pctasks.execute.constants import (
    ITEM_TEMPLATE_PATH,
    JOBS_TEMPLATE_PATH,
    TASKS_TEMPLATE_PATH,
    TRIGGER_TEMPLATE_PATH,
)

N = TypeVar("N", bound=NotificationConfig)


def template_args(
    data: Dict[str, Any],
    job_outputs: Dict[str, Any],
    task_outputs: Dict[str, Any],
    trigger_event: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    def _get_value(path: List[str]) -> Optional[TemplateValue]:
        if path[0] == JOBS_TEMPLATE_PATH:
            return find_value(job_outputs, path[1:])
        if path[0] == TASKS_TEMPLATE_PATH:
            return find_value(task_outputs, path[1:])
        if path[0] == TRIGGER_TEMPLATE_PATH:
            if not trigger_event:
                raise TemplateError("No trigger event found")
            return find_value(trigger_event, path[1:])
        return None

    return template_dict(data, _get_value)


def template_foreach(
    foreach: ForeachConfig,
    job_outputs: Dict[str, Any],
    trigger_event: Optional[Dict[str, Any]],
) -> List[Any]:
    if isinstance(foreach.items, list):
        return foreach.items

    def _get_value(path: List[str]) -> Optional[TemplateValue]:
        if path[0] == JOBS_TEMPLATE_PATH:
            return find_value(job_outputs, path[1:], strict=True)
        if path[0] == TRIGGER_TEMPLATE_PATH:
            if not trigger_event:
                raise TemplateError("No trigger event found")
            return find_value(trigger_event, path[1:], strict=True)
        raise TemplateError(
            f"Foreach items invalid: '{'.'.join(path)}'"
            "must be a list, or templated from "
            f"'{JOBS_TEMPLATE_PATH}' or '{TRIGGER_TEMPLATE_PATH}'."
        )

    items = template_str(foreach.items, _get_value)

    if not isinstance(items, list):
        raise TemplateError(f"foreach expected list of items, got {items}")

    return list(completely_flatten(items))


class ItemTemplater(Templater):
    def __init__(self, item: TemplateValue):
        self.item = item

    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        if path[0] == ITEM_TEMPLATE_PATH:
            return self.item
        return None


def template_job_with_item(
    job: JobConfig, item: TemplateValue, index: int
) -> JobConfig:
    if isinstance(item, dict):
        result = DictTemplater({"item": item}).template_model(job)
    else:
        result = ItemTemplater(item).template_model(job)
    result.id = f"{job.id}[{index}]"
    return result


def template_notification(
    notification: N,
    task_outputs: Dict[str, Any],
) -> N:
    return DictTemplater({TASKS_TEMPLATE_PATH: task_outputs}).template_model(
        notification
    )
