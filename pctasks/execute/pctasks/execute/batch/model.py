from dataclasses import dataclass
from enum import Enum
from typing import List, cast

import azure.batch.models as batchmodels

from pctasks.core.models.base import PCBaseModel


class BatchTaskId(PCBaseModel):
    batch_job_id: str
    batch_task_id: str


# Azure Batch models


class JobState(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def from_batch(
        cls, job_state: batchmodels.JobState, failed_tasks: bool
    ) -> "JobState":
        if (
            job_state == batchmodels.JobState.completed
            or job_state == batchmodels.JobState.terminating
        ):
            if failed_tasks:
                return JobState.FAILED
            else:
                return JobState.COMPLETED

        active_states = [
            batchmodels.JobState.active,
            batchmodels.JobState.deleting,
            batchmodels.JobState.disabled,
            batchmodels.JobState.disabling,
            batchmodels.JobState.enabling,
        ]

        if job_state in active_states:
            return JobState.ACTIVE

        raise ValueError(f"Unknown JobState {job_state}")


@dataclass
class JobInfo:
    state: JobState

    @classmethod
    def from_batch(
        cls, cloud_job: batchmodels.CloudJob, tasks: List[batchmodels.CloudTask]
    ) -> "JobInfo":
        failed_tasks = [
            cast(batchmodels.CloudTask, task)
            for task in tasks
            if cast(batchmodels.TaskExecutionInformation, task.execution_info).result
            == "failure"
        ]

        state = JobState.from_batch(
            cast(batchmodels.JobState, cloud_job.state), failed_tasks=any(failed_tasks)
        )

        return JobInfo(state=state)
