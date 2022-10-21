from pctasks.core.models.config import ImageConfig
from pctasks.core.models.task import TaskDefinition
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.dev.secrets import TempSecrets
from pctasks.dev.tables import TempTable
from pctasks.run.models import TaskSubmitMessage
from pctasks.run.settings import RunSettings
from pctasks.run.task.prepare import prepare_task


def test_image_key_environment_merged():
    secret_name = "SECRET_VAR"
    secret_value = "SECRET_VALUE"
    target_environment = "test-image-key-env"

    exec_settings = RunSettings.get()
    tmp_table = TempTable()
    exec_settings.image_key_table_name = tmp_table.table_config.table_name

    print(exec_settings.image_key_table_name)
    print(RunSettings.get().image_key_table_name)

    with TempSecrets({secret_name: secret_value}):
        with tmp_table as table_client:
            with ImageKeyEntryTable(lambda: (None, table_client)) as entry_table:
                entry_table.set_image(
                    "test-image-key",
                    target_environment=target_environment,
                    image_config=ImageConfig(
                        image="test-image:latest",
                        environment=[
                            "TEST_ENV_VAR=${{ secrets.SECRET_VAR }}",
                        ],
                    ),
                )

            with ImageKeyEntryTable(lambda: (None, table_client)) as entry_table:
                assert (
                    entry_table.get_image("test-image-key", target_environment)
                    is not None
                )

            run_id = "test_run_id"

            submit_msg = TaskSubmitMessage(
                dataset_id="test-dataset-id",
                instance_id="test_instance_id",
                job_id="job-id",
                partition_id="0",
                run_id=run_id,
                target_environment=target_environment,
                config=TaskDefinition(
                    id="messages_unit_test",
                    image_key="test-image-key",
                    args={"one": "two"},
                    task="dummy:task",
                ),
            )

            prepared_task = prepare_task(
                submit_msg=submit_msg,
                run_id=run_id,
                settings=exec_settings,
            )

            run_msg = prepared_task.task_run_message
            assert run_msg.config.environment
            assert "TEST_ENV_VAR" in run_msg.config.environment
            assert run_msg.config.environment["TEST_ENV_VAR"] == secret_value
