from typing import Optional

from pctasks.run.settings import RunSettings, TaskRunnerType
from pctasks.run.task.argo import ArgoTaskRunner
from pctasks.run.task.base import TaskRunner
from pctasks.run.task.batch import BatchTaskRunner
from pctasks.run.task.local import LocalTaskRunner


def get_task_runner(settings: Optional[RunSettings] = None) -> TaskRunner:
    settings = settings or RunSettings.get()

    if settings.task_runner_type == TaskRunnerType.LOCAL:
        assert settings.local_dev_endpoints_url  # Checked during settings validation
        return LocalTaskRunner(settings.local_dev_endpoints_url)
    elif settings.task_runner_type == TaskRunnerType.BATCH:
        return BatchTaskRunner(settings)
    elif settings.task_runner_type == TaskRunnerType.ARGO:
        return ArgoTaskRunner(settings)
    else:
        raise ValueError(f"Unknown task runner type: {settings.task_runner_type}")
