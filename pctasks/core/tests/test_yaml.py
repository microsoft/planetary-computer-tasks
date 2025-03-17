from pctasks.core.models.workflow import WorkflowDefinition
from pctasks.core.yaml import YamlValidationError


def test_error_handling():
    try:
        _ = WorkflowDefinition.from_yaml(
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
        assert "dataset: Field required" in error_text
