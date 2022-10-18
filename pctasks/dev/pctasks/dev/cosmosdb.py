#!/bin/bash
"""
Sets up the Cosmos DB emulator.
"""
import time
from contextlib import contextmanager
from typing import Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urljoin
from uuid import uuid1

import click
import requests
from azure.cosmos import DatabaseProxy, PartitionKey
from azure.cosmos.documents import TriggerOperation, TriggerType
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.settings import DEFAULT_DATABASE_NAME, CosmosDBSettings
from pctasks.core.utils import ignore_ssl_warnings
from pctasks.dev.settings import DevSettings

CONTAINERS: List[Tuple[Callable[[CosmosDBSettings], str], str]] = [
    (lambda settings: settings.get_workflow_runs_container_name(), "/run_id"),
    (lambda settings: settings.get_workflows_container_name(), "/workflow_id"),
    (lambda settings: settings.get_records_container_name(), "/type"),
]


def wait_for_emulator_start(url: str) -> None:
    url = urljoin(url, "_explorer/emulator.pem")
    print(f"Waiting for emulator to start via {url}...", flush=True)
    with ignore_ssl_warnings():
        try_count = 0
        while True:
            try:
                resp = requests.get(url, verify=False)
                resp.raise_for_status()
                break
            except Exception as e:
                print(f"Emulator not responding: {e}", flush=True)
                print("Retrying in 10 seconds...", flush=True)
                time.sleep(10)
                if try_count > 10:
                    raise Exception("Emulator failed to start!") from e
                try_count += 1


def update_stored_procedures(db: DatabaseProxy, settings: CosmosDBSettings) -> None:
    print("Creating stored procedures...")
    dev_settings = DevSettings.get()
    stored_procedures_dir = dev_settings.get_cosmosdb_emulator_stored_procs_dir()
    if not stored_procedures_dir.exists():
        return
    container_names = [container_name(settings) for container_name, _ in CONTAINERS]
    for container_dir in stored_procedures_dir.iterdir():
        matching_containers = [x for x in container_names if container_dir.stem in x]
        if not matching_containers:
            raise Exception(
                f"Container {container_dir.stem} not found in {container_names}"
            )
        if len(matching_containers) > 1:
            raise Exception(
                f"Multiple containers found for {container_dir.stem}: "
                f"{matching_containers}"
            )
        container_name = matching_containers[0]
        container = db.get_container_client(container_name)
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


def update_triggers(db: DatabaseProxy, settings: CosmosDBSettings) -> None:
    print("Creating triggers...")
    dev_settings = DevSettings.get()
    triggers_dir = dev_settings.get_cosmosdb_emulator_triggers_dir()
    if not triggers_dir.exists():
        return
    container_names = [container_name(settings) for container_name, _ in CONTAINERS]
    for container_dir in triggers_dir.iterdir():
        matching_containers = [x for x in container_names if container_dir.stem in x]
        if not matching_containers:
            raise Exception(
                f"Container {container_dir.stem} not found in {container_names}"
            )
        if len(matching_containers) > 1:
            raise Exception(
                f"Multiple containers found for {container_dir.stem}: "
                f"{matching_containers}"
            )
        container_name = matching_containers[0]
        container = db.get_container_client(container_name)
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


def setup_db(db: DatabaseProxy, settings: CosmosDBSettings) -> None:
    print("Creating containers...")
    for container_name, partition_key in CONTAINERS:
        name = container_name(settings)
        print(f" - {name}")
        _ = db.create_container_if_not_exists(
            name, partition_key=PartitionKey(path=partition_key)
        )

    print("Creating lease container...")
    db.create_container_if_not_exists("leases", partition_key=PartitionKey("/id"))

    update_stored_procedures(db, settings)
    update_triggers(db, settings)


def setup_cosmosdb() -> None:
    settings = CosmosDBSettings.get()
    if settings.is_cosmosdb_emulator():
        wait_for_emulator_start(settings.get_cosmosdb_url())
    with ignore_ssl_warnings():
        cosmos_client = settings.get_client()

        print("Creating database...")
        db = cosmos_client.create_database_if_not_exists(DEFAULT_DATABASE_NAME)

        setup_db(db, settings)


def rm_test_containers(settings: CosmosDBSettings, all: bool = False) -> None:
    def _rm() -> None:
        cosmos_client = settings.get_client()
        db = cosmos_client.get_database_client(settings.database)

        existing_containers = [x["id"] for x in db.list_containers()]
        if all:
            for container_name in existing_containers:
                if container_name.startswith("tmp"):
                    print(f"Deleting container {container_name}")
                    db.delete_container(container_name)
        else:
            for container_name, _ in CONTAINERS:
                name = container_name(settings)
                if name in existing_containers:
                    if not name.startswith("tmp"):
                        print(f"Skipping non-tmp container: {name}")
                        continue
                    print(f"Deleting container: {name}")
                    db.delete_container(name)

    if settings.is_cosmosdb_emulator():
        with ignore_ssl_warnings():
            _rm()
    else:
        _rm()


@click.group("cosmosdb")
def cosmosdb_cmd() -> None:
    """Commands for Cosmos DB."""
    pass


@cosmosdb_cmd.command("setup")
def setup_cmd() -> None:
    setup_cosmosdb()


@cosmosdb_cmd.command("update-stored-procedures")
def update_stored_procedures_cmd() -> None:
    settings = CosmosDBSettings.get()
    with ignore_ssl_warnings():
        cosmos_client = settings.get_client()

        db = cosmos_client.get_database_client(DEFAULT_DATABASE_NAME)
        update_stored_procedures(db, settings)


@cosmosdb_cmd.command("reset")
def reset_cmd() -> None:
    settings = CosmosDBSettings.get()
    with ignore_ssl_warnings():
        cosmos_client = settings.get_client()
        db = cosmos_client.get_database_client(DEFAULT_DATABASE_NAME)

        existing_containers = [x["id"] for x in db.list_containers()]
        for container_name, _ in CONTAINERS:
            name = container_name(settings)
            if name in existing_containers:
                print(f"Deleting container: {name}")
                db.delete_container(name)
    print("Recreating containers...")
    setup_cosmosdb()


@cosmosdb_cmd.command("rm-test-containers")
@click.option("-a", "--all", is_flag=True, help="Remove all containers with tmp prefix")
def rm_test_containers_cmd(all: bool) -> None:
    settings = CosmosDBSettings.get()
    rm_test_containers(settings, all=all)


@cosmosdb_cmd.command("clear-tmp-dbs")
def clear_tmp_dbs_cmd() -> None:
    settings = CosmosDBSettings.get()
    with ignore_ssl_warnings():
        cosmos_client = settings.get_client()
        for db in cosmos_client.list_databases():
            if db["id"].startswith("tmp-"):
                print(f"Deleting database: {db['id']}")
                cosmos_client.delete_database(db["id"])


@contextmanager
def temp_cosmosdb_if_emulator(
    containers: Optional[Dict[str, str]] = None,
) -> Iterator[CosmosDBDatabase]:
    """Create a temporary CosmosDB database.

    If `setup` is True, the database will be created with PCTasks containers
    and stored procedures. If `containers` is provided, it should be a
    dict container name -> partition key. If no connection string is provided,
    the connection string from the environment will be used.

    If the settings are not using the emulator, just return the database
    with new containers if supplied, which will be removed when the context
    exits.
    """
    settings = CosmosDBSettings.get()

    if settings.is_cosmosdb_emulator():

        suffix = uuid1().hex[:5]
        db_name = f"tmp-{suffix}"

        with ignore_ssl_warnings():
            cosmos_client = settings.get_client()
            db = cosmos_client.create_database(db_name)
            try:
                setup_db(db, settings)
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

    else:
        settings = settings.copy()
        if settings.test_container_suffix:
            settings.test_container_suffix += uuid1().hex[:5]
        else:
            settings.test_container_suffix = uuid1().hex[:5]
        cosmos_client = settings.get_client()
        db = cosmos_client.get_database_client(settings.database)
        setup_db(db, settings)
        if containers:
            print("Creating additional containers...")
            for container_name, partition_key in containers.items():
                print(f" - {container_name}")
                _ = db.create_container_if_not_exists(
                    container_name, partition_key=PartitionKey(path=partition_key)
                )
        try:
            yield CosmosDBDatabase(settings)
        finally:
            if containers:
                print("Deleting additional containers...")
                for container_name, partition_key in containers.items():
                    print(f" - {container_name}")
                    _ = db.delete_container(container_name)
            rm_test_containers(settings)


if __name__ == "__main__":
    cosmosdb_cmd()
