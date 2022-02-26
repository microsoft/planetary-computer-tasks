from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.yaml import YamlValidationError


def test_error_handling():
    try:
        _ = WorkflowConfig.from_yaml(
            """
            name: A workflow*  *with* *asterisks

            jobs:
                name: A job
                test-job:
                    tasks:
                    - id: test-task
                      image-key: ingest-prod
                      task: tests.test_submit.MockTask
                      args:
                          hello: world
        """
        )
    except YamlValidationError as e:
        error_text = str(e)
        assert "jobs -> name: value is not a valid dict" in error_text
