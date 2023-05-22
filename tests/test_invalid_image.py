import logging
import textwrap

import pytest

from pctasks.cli.cli import setup_logging
from pctasks.dev.test_utils import assert_workflow_fails, run_workflow
from pctasks.run.argo.client import ERR_IMAGE_PULL, IMAGE_PULL_BACKOFF
from tests.constants import DEFAULT_TIMEOUT

TIMEOUT_SECONDS = DEFAULT_TIMEOUT


@pytest.mark.usefixtures("cosmosdb_containers")
def test_invalid_image():
    run_id = run_workflow(
        textwrap.dedent(
            """\
        id: test-invalid-image
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
    records.print()
    errors = " ".join(
        records.job_partition_runs["invalid-image-job"][0].tasks[0].errors or []
    )
    assert IMAGE_PULL_BACKOFF in errors or ERR_IMAGE_PULL in errors


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    test_invalid_image()
    print("Tests passed!")
    exit(0)
