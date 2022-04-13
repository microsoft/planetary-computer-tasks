from pctasks.core.models.config import ImageConfig
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.dev.tables import TempTable


def test_image_key_entry_table():
    with TempTable() as tmp_table_client:
        table = ImageKeyEntryTable(get_clients=lambda: (None, tmp_table_client))

        with table:
            table.set_image(
                "test",
                target_environment="production",
                image_config=ImageConfig(
                    image="test_image:v1",
                    environment=["CONN_STR=prod_db"],
                    tags=["pool=prod_pool"],
                ),
            )

            table.set_image(
                "test",
                target_environment="staging",
                image_config=ImageConfig(
                    image="test_image:latest",
                    environment=["CONN_STR=staging_db"],
                    tags=["pool=staging_pool"],
                ),
            )

            table.set_image(
                "test",
                image_config=ImageConfig(
                    image="test_image:default", environment=["CONN_STR=default_db"]
                ),
            )

            default_image = table.get_image("test", target_environment=None)
            assert default_image
            assert default_image.get_environment() == {"CONN_STR": "default_db"}
            assert default_image.tags is None

            production_image = table.get_image("test", target_environment="production")
            assert production_image
            assert production_image.get_environment() == {"CONN_STR": "prod_db"}
            assert production_image.get_tags() == {"pool": "prod_pool"}

            staging_image = table.get_image("test", target_environment="staging")
            assert staging_image
            assert staging_image.get_environment() == {"CONN_STR": "staging_db"}
            assert staging_image.get_tags() == {"pool": "staging_pool"}
