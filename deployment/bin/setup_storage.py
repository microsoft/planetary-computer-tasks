#!/usr/bin/env python3
import argparse

from pctasks.core.constants import DEFAULT_IMAGE_KEY_TABLE_NAME
from pctasks.core.models.config import ImageConfig
from pctasks.core.tables.config import ImageKeyEntryTable


def setup_storage(
    acr: str,
    account_name: str,
    endpoint_url: str,
    image_tag: str,
) -> None:
    # Setting up image key table.
    table_name = DEFAULT_IMAGE_KEY_TABLE_NAME

    with ImageKeyEntryTable.from_account_key(
        account_url=endpoint_url,
        account_name=account_name,
        table_name=table_name,
        account_key=None,
    ) as image_key_table:
        image_key_table.set_image(
            "ingest",
            ImageConfig(
                image=f"{acr}.azurecr.io/pctasks-ingest:{image_tag}",
                environment=[
                    "DB_CONNECTION_STRING=${{ secrets.pgstac-connection-string }}",
                ],
                tags=["batch_pool_id=ingest_pool"],
            ),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup deployed PCTasks storage.")
    parser.add_argument("acr", help="The Azure Container Registry name.")
    parser.add_argument("account_name", help="Storage account name.")
    parser.add_argument("--url", help="Endpoint URL.")
    parser.add_argument("--tag", help="Image tag.")

    args = parser.parse_args()
    setup_storage(args.acr, args.account_name, args.url, args.tag)
