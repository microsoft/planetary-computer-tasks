from typing import Optional

from pctasks.run.settings import RunSettings
from pctasks.run.task.base import TaskRunner
from pctasks.run.task.batch import BatchTaskRunner
from pctasks.run.task.local import LocalTaskRunner


def get_executor(settings: Optional[RunSettings] = None) -> TaskRunner:
    settings = settings or RunSettings.get()

    if settings.local_executor_url:
        return LocalTaskRunner(settings.local_executor_url)
    else:
        return BatchTaskRunner(settings)
