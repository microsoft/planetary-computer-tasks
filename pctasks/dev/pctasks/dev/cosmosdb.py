#!/bin/bash
"""
Sets up the Cosmos DB emulator.
"""
from contextlib import contextmanager
from typing import Dict, Iterator, Optional
from uuid import uuid1

import click
from azure.cosmos import CosmosClient, DatabaseProxy, PartitionKey
from azure.cosmos.documents import TriggerOperation, TriggerType
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.settings import (
    DEFAULT_DATABASE_NAME,
    DEFAULT_RECORDS_CONTAINER,
    DEFAULT_WORKFLOW_RUNS_CONTAINER,
    DEFAULT_WORKFLOWS_CONTAINER,
    CosmosDBSettings,
)
from pctasks.core.utils import ignore_ssl_warnings
from pctasks.dev.constants import (
    COSMOSDB_EMULATOR_ACCOUNT_KEY,
    get_cosmosdb_emulator_url,
)
from pctasks.dev.settings import DevSettings

CONTAINERS = {
    DEFAULT_WORKFLOW_RUNS_CONTAINER: "/run_id",
    DEFAULT_WORKFLOWS_CONTAINER: "/workflow_id",
    DEFAULT_RECORDS_CONTAINER: "/type",
}


def update_stored_procedures(db: DatabaseProxy) -> None:
    print("Creating stored procedures...")
    settings = DevSettings.get()
    stored_procedures_dir = settings.get_cosmosdb_emulator_stored_procs_dir()
    for container_dir in stored_procedures_dir.iterdir():
        container = db.get_container_client(container_dir.stem)
        try:
            container.read()
        except CosmosResourceNotFoundError as e:
            raise Exception(
                f"Container {container_dir.stem} for stored procs not found"
            ) from e

        print(f"  - Container: {container.id}")
        scripts = container.scripts
        for sproc_path in container_dir.glob("*.js"):
            script_id = sproc_path.stem
            print(f"     {script_id}", end=" ")
            if any(
                scripts.query_stored_procedures(
                    "SELECT * FROM c WHERE c.id = @id",
                    parameters=[{"name": "@id", "value": script_id}],  # type: ignore
                )
            ):
                print("(update)")
                scripts.replace_stored_procedure(
                    script_id, {"id": script_id, "body": sproc_path.read_text()}
                )
            else:
                print("(create)")
                scripts.create_stored_procedure(
                    {"id": script_id, "body": sproc_path.read_text()}
                )


def update_triggers(db: DatabaseProxy) -> None:
    print("Creating triggers...")
    settings = DevSettings.get()
    triggers_dir = settings.get_cosmosdb_emulator_triggers_dir()
    for container_dir in triggers_dir.iterdir():
        container = db.get_container_client(container_dir.stem)
        try:
            container.read()
        except CosmosResourceNotFoundError as e:
            raise Exception(
                f"Container {container_dir.stem} for triggers not found"
            ) from e

        print(f"  - Container: {container.id}")
        scripts = container.scripts
        for trigger_path in container_dir.glob("*.js"):
            script_id = trigger_path.stem
            parts = script_id.split("-")
            if (
                not len(parts) == 3
                or (parts[0] not in [TriggerType.Pre, TriggerType.Post])
                or (
                    parts[1]
                    not in [
                        TriggerOperation.All,
                        TriggerOperation.Create,
                        TriggerOperation.Replace,
                        TriggerOperation.Delete,
                    ]
                )
            ):
                raise Exception(f"Invalid trigger path: {trigger_path}")

            print(f"     {script_id}", end=" ")
            trigger_definition = {
                "id": script_id,
                "serverScript": trigger_path.read_text(),
                "triggerType": parts[0],
                "triggerOperation": parts[1],
            }
            if any(
                scripts.query_triggers(
                    "SELECT * FROM c WHERE c.id = @id",
                    parameters=[{"name": "@id", "value": script_id}],  # type: ignore
                )
            ):
                print("(update)")
                scripts.replace_trigger(script_id, trigger_definition)
            else:
                print("(create)")
                scripts.create_trigger(trigger_definition)


def setup_db(db: DatabaseProxy) -> None:
    print("Creating containers...")
    for container_name, partition_key in CONTAINERS.items():
        print(f" - {container_name}")
        _ = db.create_container_if_not_exists(
            container_name, partition_key=PartitionKey(path=partition_key)
        )

    print("Creating lease container...")
    db.create_container_if_not_exists("leases", partition_key=PartitionKey("/id"))

    update_stored_procedures(db)
    update_triggers(db)


def setup_cosmosdb() -> None:
    with ignore_ssl_warnings():
        cosmos_client = CosmosClient(
            url=get_cosmosdb_emulator_url(),
            credential=COSMOSDB_EMULATOR_ACCOUNT_KEY,
            connection_verify=False,
        )

        print("Creating database...")
        db = cosmos_client.create_database_if_not_exists(DEFAULT_DATABASE_NAME)

        setup_db(db)


@click.group("cosmosdb")
def cosmosdb_cmd() -> None:
    """Commands for Cosmos DB."""
    pass


@cosmosdb_cmd.command("setup")
def setup_cmd() -> None:
    setup_cosmosdb()


@cosmosdb_cmd.command("update-stored-procedures")
def update_stored_procedures_cmd() -> None:
    with ignore_ssl_warnings():
        cosmos_client = CosmosClient(
            url=get_cosmosdb_emulator_url(),
            credential=COSMOSDB_EMULATOR_ACCOUNT_KEY,
            connection_verify=False,
        )

        db = cosmos_client.get_database_client(DEFAULT_DATABASE_NAME)
        update_stored_procedures(db)


@cosmosdb_cmd.command("reset")
def reset_cmd() -> None:
    with ignore_ssl_warnings():
        cosmos_client = CosmosClient(
            url=get_cosmosdb_emulator_url(),
            credential=COSMOSDB_EMULATOR_ACCOUNT_KEY,
            connection_verify=False,
        )
        db = cosmos_client.get_database_client(DEFAULT_DATABASE_NAME)

        existing_containers = [x["id"] for x in db.list_containers()]
        for container_name in CONTAINERS:
            if container_name in existing_containers:
                print(f"Deleting container: {container_name}")
                db.delete_container(container_name)
    print("Recreating containers...")
    setup_cosmosdb()


@cosmosdb_cmd.command("clear-tmp-dbs")
def clear_tmp_dbs_cmd() -> None:
    with ignore_ssl_warnings():
        cosmos_client = CosmosClient(
            url=get_cosmosdb_emulator_url(),
            credential=COSMOSDB_EMULATOR_ACCOUNT_KEY,
            connection_verify=False,
        )
        for db in cosmos_client.list_databases():
            if db["id"].startswith("tmp-"):
                print(f"Deleting database: {db['id']}")
                cosmos_client.delete_database(db["id"])


@contextmanager
def temp_cosmosdb(
    setup: bool = True,
    containers: Optional[Dict[str, str]] = None,
    conn_str: Optional[str] = None,
) -> Iterator[CosmosDBDatabase]:
    """Create a temporary CosmosDB database.

    If `setup` is True, the database will be created with PCTasks containers
    and stored procedures. If `containers` is provided, it should be a
    dict container name -> partition key. If no connection string is provided,
    the connection string from the environment will be used.
    """
    settings = CosmosDBSettings.get().copy()
    if conn_str is not None:
        settings.connection_string = conn_str

    suffix = uuid1().hex[:5]
    db_name = f"tmp-{suffix}"

    with ignore_ssl_warnings():
        cosmos_client = settings.get_client()
        db = cosmos_client.create_database(db_name)
        try:
            if setup:
                setup_db(db)
            if containers is not None:
                for container in containers:
                    db.create_container_if_not_exists(
                        container,
                        partition_key=PartitionKey(path=containers[container]),
                    )

            settings.database = db_name
            yield CosmosDBDatabase(settings)

        finally:
            cosmos_client.delete_database(db_name)


@cosmosdb_cmd.command("test-temp")
def test_tmp_cmd() -> None:
    with ignore_ssl_warnings():
        with temp_cosmosdb() as _:
            ...


if __name__ == "__main__":
    cosmosdb_cmd()
