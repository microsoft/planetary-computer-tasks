from pctasks.core.cosmos.containers.workflows import WorkflowsContainer
from pctasks.core.models.run import (
    JobRunRecord,
    JobRunStatus,
    RunRecordType,
    WorkflowRunRecord,
)
from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.workflow import (
    JobDefinition,
    Workflow,
    WorkflowDefinition,
    WorkflowRecord,
    WorkflowRunStatus,
)


def test_workflow_runs_pagination(cosmosdb_containers):
    workflow_id = "test-workflow"
    run_id_1 = "test-run-1"
    run_id_2 = "test-run-2"
    job_id = "test-job"
    dataset_id = "test-dataset"
    workflow = WorkflowRecord.from_workflow(
        Workflow(
            definition=WorkflowDefinition(
                name="Test Workflow",
                dataset_id="test-dataset",
                jobs={
                    "test-job": JobDefinition(
                        id="test-job",
                        tasks=[
                            TaskDefinition(
                                id="test-task",
                                image="test-image",
                                task="test:task",
                            )
                        ],
                    )
                },
            ),
            id=workflow_id,
        ),
    )

    with WorkflowsContainer(WorkflowRecord, db=cosmosdb_containers) as workflows:
        workflows.put(workflow)
        assert workflows.get(workflow_id, partition_key=workflow_id)

        with WorkflowsContainer(
            WorkflowRunRecord, db=cosmosdb_containers
        ) as workflow_runs:
            workflow_run_1 = WorkflowRunRecord(
                workflow_id=workflow_id,
                run_id=run_id_1,
                dataset_id=dataset_id,
                status=WorkflowRunStatus.SUBMITTED,
                jobs=[
                    JobRunRecord(
                        status=JobRunStatus.PENDING, run_id=run_id_1, job_id=job_id
                    )
                ],
            )

            workflow_runs.put(workflow_run_1)
            assert workflow_runs.get(run_id_1, partition_key=workflow_id)

            workflow_run_2 = WorkflowRunRecord(
                workflow_id=workflow_id,
                run_id=run_id_2,
                dataset_id=dataset_id,
                status=WorkflowRunStatus.RUNNING,
                jobs=[
                    JobRunRecord(
                        status=JobRunStatus.RUNNING, run_id=run_id_2, job_id=job_id
                    )
                ],
            )

            workflow_runs.put(workflow_run_2)
            assert workflow_runs.get(run_id_2, partition_key=workflow_id)

            pages = list(
                workflow_runs.query_paged(
                    partition_key=workflow_id,
                    query="SELECT * FROM c WHERE c.workflow_id = @workflow_id "
                    "and c.type = @type",
                    parameters={
                        "workflow_id": workflow_id,
                        "type": RunRecordType.WORKFLOW_RUN,
                    },
                    page_size=1,
                )
            )

            assert len(pages) == 2

            pages2 = list(
                workflow_runs.query_paged(
                    partition_key=workflow_id,
                    query="SELECT * FROM c WHERE c.workflow_id = @workflow_id "
                    "and c.type = @type",
                    parameters={
                        "workflow_id": workflow_id,
                        "type": RunRecordType.WORKFLOW_RUN,
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

            assert items1_2[0].run_id == items2_1[0].run_id

            # Test job_run.task_group_count trigger update

            def fetch_workflow() -> WorkflowRecord:
                fetched_workflow = workflows.get(workflow_id, partition_key=workflow_id)
                assert fetched_workflow is not None
                return fetched_workflow

            workflow = fetch_workflow()
            assert workflow.workflow_run_counts[WorkflowRunStatus.SUBMITTED] == 1
            assert workflow.workflow_run_counts[WorkflowRunStatus.RUNNING] == 1

            workflow_run_1.set_status(WorkflowRunStatus.RUNNING)
            workflow_runs.put(workflow_run_1)

            workflow = fetch_workflow()
            assert workflow.workflow_run_counts[WorkflowRunStatus.SUBMITTED] == 0
            assert workflow.workflow_run_counts[WorkflowRunStatus.RUNNING] == 2
