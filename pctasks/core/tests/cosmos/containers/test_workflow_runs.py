from typing import Any, List, Optional, Type

from pctasks.core.cosmos.containers.workflow_runs import T, WorkflowRunsContainer
from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.run import (
    JobPartitionRunRecord,
    JobPartitionRunStatus,
    JobRunRecord,
    JobRunStatus,
    RunRecordType,
    TaskRunRecord,
    TaskRunStatus,
    WorkflowRunRecord,
)
from pctasks.core.models.workflow import WorkflowRunStatus


class MockWorkflowRunsContainer(WorkflowRunsContainer[T]):
    """Mock to count the number of times put is called."""

    def __init__(
        self,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
    ) -> None:
        self.put_count = 0
        super().__init__(model_type, db, settings)

    def put(self, *args: Any, **kwargs: Any):
        self.put_count += 1
        return super().put(*args, **kwargs)


def test_job_part_pagination(cosmosdb_containers):
    run_id = "test-run"
    job_id = "test-job"
    dataset_id = "test-dataset"
    workflow_run = WorkflowRunRecord(
        workflow_id="test-workflow",
        run_id=run_id,
        dataset_id=dataset_id,
        status=WorkflowRunStatus.RUNNING,
        jobs=[JobRunRecord(status=JobRunStatus.RUNNING, run_id=run_id, job_id=job_id)],
    )

    with WorkflowRunsContainer(
        WorkflowRunRecord, db=cosmosdb_containers
    ) as workflow_runs:
        workflow_runs.put(workflow_run)

        assert workflow_runs.get(run_id, partition_key=run_id)

        job_parts = [
            JobPartitionRunRecord(
                job_id=job_id,
                status=JobPartitionRunStatus.RUNNING,
                run_id=run_id,
                partition_id="0",
                tasks=[
                    TaskRunRecord(
                        status=TaskRunStatus.RUNNING,
                        run_id=run_id,
                        job_id=job_id,
                        partition_id="0",
                        task_id="test-task",
                    )
                ],
            ),
            JobPartitionRunRecord(
                job_id=job_id,
                status=JobPartitionRunStatus.PENDING,
                run_id=run_id,
                partition_id="1",
                tasks=[
                    TaskRunRecord(
                        status=TaskRunStatus.PENDING,
                        run_id=run_id,
                        job_id=job_id,
                        partition_id="1",
                        task_id="test-task",
                    )
                ],
            ),
        ]

        with WorkflowRunsContainer(
            JobPartitionRunRecord, db=cosmosdb_containers
        ) as job_partition_runs:
            for task_group_run in job_parts:
                job_partition_runs.put(task_group_run)

            pages = list(
                job_partition_runs.query_paged(
                    partition_key=run_id,
                    query=(
                        "SELECT * FROM c WHERE c.job_id = @job_id " "and c.type = @type"
                    ),
                    parameters={
                        "@job_id": job_id,
                        "type": RunRecordType.JOB_PARTITION_RUN,
                    },
                    page_size=1,
                )
            )

            assert len(pages) == 2

            pages2 = list(
                job_partition_runs.query_paged(
                    partition_key=run_id,
                    query=(
                        "SELECT * FROM c WHERE c.job_id = @job_id " "and c.type = @type"
                    ),
                    parameters={
                        "@job_id": job_id,
                        "type": RunRecordType.JOB_PARTITION_RUN,
                    },
                    page_size=1,
                    continuation_token=pages[0].continuation_token,
                )
            )

            assert len(pages2) == 1

            items1_2 = list(pages[1])
            items2_1 = list(pages2[0])

            assert len(items1_2) == 1
            assert len(items2_1) == 1

            assert items1_2[0].partition_id == items2_1[0].partition_id

            # Test job_run.job_partition_counts trigger update

            def fetch_job_run() -> JobRunRecord:
                fetched_workflow_run = workflow_runs.get(run_id, partition_key=run_id)
                assert fetched_workflow_run is not None
                assert len(fetched_workflow_run.jobs) == 1
                return fetched_workflow_run.jobs[0]

            job_run = fetch_job_run()
            assert job_run.job_partition_counts[JobPartitionRunStatus.PENDING] == 1
            assert job_run.job_partition_counts[JobPartitionRunStatus.RUNNING] == 1

            job_parts[1].set_status(JobPartitionRunStatus.RUNNING)
            job_partition_runs.put(job_parts[1])

            job_run = fetch_job_run()
            assert job_run.job_partition_counts[JobPartitionRunStatus.PENDING] == 0
            assert job_run.job_partition_counts[JobPartitionRunStatus.RUNNING] == 2


def test_job_part_bulk_put(cosmosdb_containers):
    run_id = "test-run-bulk-put"
    job_id = "test-job"
    dataset_id = "test-dataset"
    workflow_run = WorkflowRunRecord(
        workflow_id="test-workflow",
        run_id=run_id,
        dataset_id=dataset_id,
        status=WorkflowRunStatus.RUNNING,
        jobs=[JobRunRecord(status=JobRunStatus.RUNNING, run_id=run_id, job_id=job_id)],
    )

    with WorkflowRunsContainer(
        WorkflowRunRecord, db=cosmosdb_containers
    ) as workflow_runs:
        workflow_runs.put(workflow_run)

        assert workflow_runs.get(run_id, partition_key=run_id)

        job_parts: List[JobPartitionRunRecord] = []
        for i in range(100):
            job_parts.append(
                JobPartitionRunRecord(
                    job_id=job_id,
                    status=JobPartitionRunStatus.RUNNING,
                    run_id=run_id,
                    partition_id=str(i),
                    tasks=[
                        TaskRunRecord(
                            status=TaskRunStatus.RUNNING,
                            run_id=run_id,
                            job_id=job_id,
                            partition_id=str(i),
                            task_id="test-task",
                        )
                    ],
                ),
            )

        mock_job_partition_runs = MockWorkflowRunsContainer(
            JobPartitionRunRecord, db=cosmosdb_containers
        )
        with mock_job_partition_runs:
            mock_job_partition_runs.bulk_put(job_parts)

            pages = list(
                mock_job_partition_runs.query_paged(
                    partition_key=run_id,
                    query=(
                        "SELECT * FROM c WHERE c.job_id = @job_id " "and c.type = @type"
                    ),
                    parameters={
                        "@job_id": job_id,
                        "type": RunRecordType.JOB_PARTITION_RUN,
                    },
                    page_size=50,
                )
            )

            assert len(pages) == 2

        assert mock_job_partition_runs.put_count == 0
