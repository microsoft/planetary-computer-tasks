from functools import lru_cache

from pydantic import BaseSettings

from pctasks.core.constants import (
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    ENV_VAR_PCTASK_PREFIX,
)


class TaskSettings(BaseSettings):
    task_runs_table_name: str = DEFAULT_TASK_RUN_RECORD_TABLE_NAME

    class Config:
        env_prefix = ENV_VAR_PCTASK_PREFIX

    @classmethod
    @lru_cache(maxsize=1)
    def get(cls) -> "TaskSettings":
        return cls()
