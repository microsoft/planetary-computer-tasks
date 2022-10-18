from pctasks.core.models.workflow import WorkflowDefinition
from pctasks.run.dag import sort_jobs


def test_sort_jobs():
    jobs = WorkflowDefinition.from_yaml(
        """
            name: Test job sort workflow
            dataset: microsoft/test-dataset

            jobs:
                job2:
                    needs: job1
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
                job1:
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world

                job3:
                    needs:
                        - job2
                        - job4
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
                job4:
                    needs:
                        - job2
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
                job5:
                    tasks:
                      - id: test-task
                        image_key: ingest-prod
                        task: tests.test_submit.MockTask
                        args:
                          hello: world
        """
    ).jobs.values()

    sorted_job_ids = [j.id for j in sort_jobs(list(jobs))]

    assert sorted_job_ids == ["job1", "job5", "job2", "job4", "job3"]
