from typing import Optional

from pctasks.core.models.task import TaskRunMessage
from pctasks.core.tables.base import ModelTableService


class TaskRunMessageTable(ModelTableService[TaskRunMessage]):
    _model = TaskRunMessage

    def insert_message(self, msg: TaskRunMessage) -> None:
        self.insert(
            partition_key=msg.config.job_id,
            row_key=msg.config.run_id,
            entity=msg,
        )

    def upsert_message(self, msg: TaskRunMessage) -> None:
        self.upsert(
            partition_key=msg.config.job_id,
            row_key=msg.config.run_id,
            entity=msg,
        )

    def update_message(self, msg: TaskRunMessage) -> None:
        self.update(
            partition_key=msg.config.job_id,
            row_key=msg.config.run_id,
            entity=msg,
        )

    def get_message(self, job_id: str, run_id: str) -> Optional[TaskRunMessage]:
        return self.get(partition_key=job_id, row_key=run_id)
