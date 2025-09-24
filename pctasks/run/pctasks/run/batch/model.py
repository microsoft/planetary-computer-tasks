from dataclasses import dataclass
from enum import Enum
from typing import List, cast

import azure.batch.models as batchmodels

from pctasks.core.models.base import PCBaseModel


class BatchTaskId(PCBaseModel):
    batch_job_id: str
    batch_task_id: str


# Azure Batch models


class BatchJobState(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def from_batch(
        cls, job_state: batchmodels.BatchJobState, failed_tasks: bool
    ) -> "BatchJobState":
        if (
            job_state == batchmodels.BatchJobState.COMPLETED
            or job_state == batchmodels.BatchJobState.TERMINATING
        ):
            if failed_tasks:
                return BatchJobState.FAILED
            else:
                return BatchJobState.COMPLETED

        active_states = [
            batchmodels.BatchJobState.ACTIVE,
            batchmodels.BatchJobState.DELETING,
            batchmodels.BatchJobState.DISABLED,
            batchmodels.BatchJobState.DISABLING,
            batchmodels.BatchJobState.ENABLING,
        ]

        if job_state in active_states:
            return BatchJobState.ACTIVE

        raise ValueError(f"Unknown JobState {job_state}")


@dataclass
class BatchJobInfo:
    state: BatchJobState

    @classmethod
    def from_batch(
        cls, cloud_job: batchmodels.BatchJob, tasks: List[batchmodels.BatchTask]
    ) -> "BatchJobInfo":
        failed_tasks = [
            cast(batchmodels.BatchTask, task)
            for task in tasks
            if cast(batchmodels.BatchTaskExecutionInfo, task.execution_info).result
            == "failure"
        ]

        state = BatchJobState.from_batch(
            cast(batchmodels.BatchJobState, cloud_job.state),
            failed_tasks=any(failed_tasks),
        )

        return BatchJobInfo(state=state)
