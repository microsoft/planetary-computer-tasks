#!/bin/python3
import argparse
from datetime import datetime, timedelta
from typing import Optional

from azure.data.tables import generate_table_sas, TableSasPermissions
from azure.core.credentials import AzureNamedKeyCredential

from pctasks.core.constants import DEFAULT_IMAGE_KEY_TABLE_NAME
from pctasks.core.models.config import ImageConfig
from pctasks.core.tables.config import ImageKeyEntryTable


def setup_storage(
    acr: str, account_name: str, account_key: str, endpoint_url: Optional[str]
) -> None:
    # Setting up image key table.
    table_name = DEFAULT_IMAGE_KEY_TABLE_NAME
    tables_cred = AzureNamedKeyCredential(name=account_name, key=account_key)

    sas_token = generate_table_sas(
        credential=tables_cred,
        table_name=table_name,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=TableSasPermissions(
            add=True, upsert=True, read=True, write=True, update=True
        ),
    )

    with ImageKeyEntryTable.from_sas_token(
        account_url=endpoint_url or f"https://{account_name}.table.core.windows.net",
        sas_token=sas_token,
        table_name=table_name,
    ) as image_key_table:
        image_key_table.set_image(
            "ingest",
            ImageConfig(
                image=f"{acr}.azurecr.io/pctasks-ingest:latest",
                environment=[
                    "DB_CONNECTION_STRING=${{ secrets.pgstac-connection-string }}",
                ],
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup deployed PCTasks storage.")
    parser.add_argument("acr", help="The Azure Container Registry name.")
    parser.add_argument("account_name", help="Storage account name.")
    parser.add_argument("account_key", help="Storage account key.")
    parser.add_argument("--url", help="Endpoint URL.")

    args = parser.parse_args()
    setup_storage(args.acr, args.account_name, args.account_key, args.url)
