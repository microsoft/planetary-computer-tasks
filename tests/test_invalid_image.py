import textwrap

from pctasks.dev.test_utils import assert_workflow_fails, run_workflow
from pctasks.run.argo.client import ERR_IMAGE_PULL, IMAGE_PULL_BACKOFF


TIMEOUT_SECONDS = 60


def test_invalid_image():

    run_id = run_workflow(
        textwrap.dedent(
            """\

        name: Test invalid image
        dataset: microsoft/test-invalid-image
        target_environment: staging

        jobs:
            invalid-image-job:
                name: Invalid image job
                tasks:
                - id: invalid-image-task
                  image: bad-image:latest
                  task: tests.tasks:none

            """
        )
    )

    records = assert_workflow_fails(run_id, timeout_seconds=TIMEOUT_SECONDS)
    errors = " ".join(
        records.jobs["invalid-image-job"].tasks["invalid-image-task"].errors or []
    )
    assert IMAGE_PULL_BACKOFF in errors or ERR_IMAGE_PULL in errors
