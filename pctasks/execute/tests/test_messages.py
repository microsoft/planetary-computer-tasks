from pctasks.core.models.base import TargetEnvironment
from pctasks.core.models.config import ImageConfig
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.task import TaskConfig
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.dev.secrets import TempSecrets
from pctasks.dev.tables import TempTable
from pctasks.execute.models import TaskSubmitMessage
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.run_message import submit_msg_to_task_run_msg


def test_image_key_environment_merged():
    secret_name = "SECRET_VAR"
    secret_value = "SECRET_VALUE"

    exec_settings = ExecutorSettings.get()
    tmp_table = TempTable()
    exec_settings.image_key_table_name = tmp_table.table_config.table_name

    print(exec_settings.image_key_table_name)
    print(ExecutorSettings.get().image_key_table_name)

    with TempSecrets({secret_name: secret_value}):
        with tmp_table as table_client:
            with ImageKeyEntryTable(lambda: (None, table_client)) as entry_table:
                entry_table.set_image(
                    "test-image-key",
                    target_environment=TargetEnvironment.PRODUCTION,
                    image_config=ImageConfig(
                        image="test-image:latest",
                        environment=[
                            "TEST_ENV_VAR=${{ secrets.SECRET_VAR }}",
                        ],
                    ),
                )

            with ImageKeyEntryTable(lambda: (None, table_client)) as entry_table:
                assert (
                    entry_table.get_image(
                        "test-image-key", TargetEnvironment.PRODUCTION
                    )
                    is not None
                )

            run_id = "test_run_id"

            submit_msg = TaskSubmitMessage(
                dataset=DatasetIdentifier(name="test-dataset-id"),
                instance_id="test_instance_id",
                job_id="job-id",
                run_id=run_id,
                target_environment=TargetEnvironment.PRODUCTION,
                config=TaskConfig(
                    id="messages_unit_test",
                    image_key="test-image-key",
                    args={"one": "two"},
                    task="dummy:task",
                ),
            )

            run_msg = submit_msg_to_task_run_msg(
                submit_msg=submit_msg,
                run_id=run_id,
                settings=exec_settings,
            )

            assert run_msg.config.environment
            assert "TEST_ENV_VAR" in run_msg.config.environment
            assert run_msg.config.environment["TEST_ENV_VAR"] == secret_value
