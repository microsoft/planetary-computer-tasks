import json
import pathlib
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch

import orjson
import pytest
from pypgstac.load import Methods

from pctasks.core.models.task import FailedTaskResult
from pctasks.core.utils import grouped
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.models import (
    IngestNdjsonInput,
    IngestTaskConfig,
    IngestTaskInput,
    NdjsonFolder,
)
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.ingest_task.task import ingest_task
from tests.conftest import ingest_test_environment

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "data-files/test_collection.json"
TEST_SINGLE_ITEM = HERE / "data-files/items/item1.json"
TEST_NDJSON = HERE / "data-files/items/items.ndjson"
TEST_DUPE_NDJSON = HERE / "data-files/items/items_dupe.ndjson"


@pytest.fixture
def pgstac_fixture() -> Generator[Tuple[PgSTAC, Mock, Mock], None, None]:
    with (
        patch("pypgstac.db.PgstacDB") as MockPgstacDB,
        patch("pypgstac.load.Loader") as MockLoader,
    ):
        mock_db = MockPgstacDB.return_value
        mock_loader = MockLoader.return_value

        pgstac = PgSTAC("postgresql://username:password@database:5432/postgis")
        yield (pgstac, mock_db, mock_loader)


@pytest.fixture
def dupe_ndjson_lines() -> List[bytes]:
    with open(TEST_DUPE_NDJSON, "r") as f:
        return [line.strip().encode("utf-8") for line in f.readlines() if line.strip()]


@pytest.fixture
def capture_loader_calls() -> Tuple[MagicMock, List[dict]]:
    captured_calls = []

    def mock_load_items(
        items_iter: Generator[bytes, None, None], insert_mode: Methods
    ) -> None:
        items_list = list(items_iter)
        captured_calls.append({"items": items_list, "mode": insert_mode})
        return None

    mock_loader = MagicMock()
    mock_loader.load_items.side_effect = mock_load_items

    return mock_loader, captured_calls


def test_single_item_ingest() -> None:
    """Test ingesting Items through the ingest task logic."""

    task_context = MockTaskContext.default()

    with ingest_test_environment():
        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest an item
        with open(TEST_SINGLE_ITEM, "r") as f:
            item = json.load(f)

        print(json.dumps(IngestTaskInput(content=item).dict(), indent=2))
        result = ingest_task.run(
            input=IngestTaskInput(content=item), context=task_context
        )

        assert not isinstance(result, FailedTaskResult)


def test_ndjson_ingest() -> None:
    """Test ingesting Items through the ingest task logic."""

    task_context = MockTaskContext.default()

    with ingest_test_environment():
        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest Ndjson
        message_data = IngestTaskInput(
            content=IngestNdjsonInput(uris=[str(TEST_NDJSON.absolute())])
        )

        result = ingest_task.run(input=message_data, context=task_context)

        assert not isinstance(result, FailedTaskResult)


def test_ingest_ndjson_add_service_principal() -> None:
    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
        add_service_principal=True,
    )

    assert result.environment

    assert result.environment["AZURE_TENANT_ID"] == "${{ secrets.task-tenant-id }}"
    assert result.environment["AZURE_CLIENT_ID"] == "${{ secrets.task-client-id }}"
    assert (
        result.environment["AZURE_CLIENT_SECRET"] == "${{ secrets.task-client-secret }}"
    )

    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
        environment={"AZURE_TENANT_ID": "test"},
        add_service_principal=True,
    )

    assert result.environment

    assert result.environment["AZURE_TENANT_ID"] == "test"
    assert result.environment["AZURE_CLIENT_ID"] == "${{ secrets.task-client-id }}"
    assert (
        result.environment["AZURE_CLIENT_SECRET"] == "${{ secrets.task-client-secret }}"
    )

    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
    )
    assert result.environment is not None
    assert "AZURE_TENANT_ID" not in result.environment
    assert "AZURE_CLIENT_ID" not in result.environment
    assert "AZURE_CLIENT_SECRET" not in result.environment


def test_empty_ndjson_ingest(tmp_path: Path) -> None:
    """Test ingesting an empty item collection works."""

    task_context = MockTaskContext.default()

    p = tmp_path / "test.ndjson"
    p.write_text("")

    with ingest_test_environment():
        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest Ndjson
        message_data = IngestTaskInput(
            content=IngestNdjsonInput(uris=[str(p.absolute())])
        )

        result = ingest_task.run(input=message_data, context=task_context)

        assert not isinstance(result, FailedTaskResult)


def test_ingest_dupe_items_ndjson() -> None:
    task_context = MockTaskContext.default()

    with ingest_test_environment():
        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest Ndjson
        message_data = IngestTaskInput(
            content=IngestNdjsonInput(uris=[str(TEST_DUPE_NDJSON.absolute())])
        )

        result = ingest_task.run(input=message_data, context=task_context)

        assert not isinstance(result, FailedTaskResult)


def test_unique_items_deduplication(
    pgstac_fixture: Tuple[PgSTAC, Mock, Mock],
    dupe_ndjson_lines: List[bytes],
) -> None:
    unique_items = list(
        pgstac_fixture[0].unique_items(
            dupe_ndjson_lines, lambda b: orjson.loads(b)["id"]
        )
    )

    assert len(dupe_ndjson_lines) == 5
    assert len(unique_items) == 3

    unique_ids = [orjson.loads(item)["id"] for item in unique_items]
    assert len(unique_ids) == 3
    assert unique_ids == ["item1", "item2", "item3"]


def test_unique_items_grouped_deduplication(
    pgstac_fixture: Tuple[PgSTAC, Mock, Mock],
    dupe_ndjson_lines: List[bytes],
) -> None:
    unique_items = list(
        pgstac_fixture[0].unique_items(
            dupe_ndjson_lines, lambda b: orjson.loads(b)["id"]
        )
    )
    unique_ids = [orjson.loads(item)["id"] for item in unique_items]

    assert len(dupe_ndjson_lines) == 5
    assert len(unique_ids) == 3

    groups = grouped(unique_items, size=3)

    seen_items: List[str] = []
    for group in groups:
        assert group
        seen_items.extend(orjson.loads(item)["id"] for item in group)

    assert len(seen_items) == 3
    assert unique_ids == seen_items


@pytest.mark.parametrize(
    "insert_group_size, mode", [(None, Methods.upsert), (2, Methods.insert)]
)
def test_ingest_items_deduplication_and_grouping(
    pgstac_fixture: Tuple[PgSTAC, Mock, Mock],
    dupe_ndjson_lines: List[bytes],
    insert_group_size: Optional[int],
    mode: Methods,
) -> None:
    captured_groups: List[Dict[str, List[bytes]]] = []
    modes_passed: List[Methods] = []

    # gets the groups from the actual code path to evaluate without side effects
    def mock_load_items(
        items_iter: Generator[bytes, None, None], insert_mode: Methods
    ) -> None:
        items_list = list(items_iter)
        captured_groups.append({"items": items_list})
        modes_passed.append(insert_mode)
        return None

    pgstac_fixture[2].load_items = mock_load_items

    pgstac_fixture[0].ingest_items(
        dupe_ndjson_lines, mode=Methods.upsert, insert_group_size=insert_group_size
    )

    expected_group_count = 1 if insert_group_size is None else insert_group_size

    assert (
        len(captured_groups) == expected_group_count
    ), f"Expected {expected_group_count} groups"

    all_items = []
    for group in captured_groups:
        all_items.extend(group["items"])

    assert len(all_items) == 3, "Should have 3 unique items after deduplication"

    all_ids = [orjson.loads(item)["id"] for item in all_items]
    assert len(all_ids) == len(set(all_ids)), "No duplicates across groups"
    assert set(all_ids) == {"item1", "item2", "item3"}, "All items correctly included"


@pytest.mark.parametrize("mode", [Methods.upsert, Methods.insert])
def test_ingest_items_with_different_modes(
    pgstac_fixture: Tuple[PgSTAC, Mock, Mock],
    dupe_ndjson_lines: List[bytes],
    mode: Methods,
) -> None:
    modes_passed = []

    def mock_load_items(
        items_iter: Generator[bytes, None, None], insert_mode: Methods
    ) -> None:
        modes_passed.append(insert_mode)
        list(items_iter)
        return None

    pgstac_fixture[2].load_items = mock_load_items

    pgstac_fixture[0].ingest_items(dupe_ndjson_lines, mode=mode)

    assert len(modes_passed) == 1, "load_items should be called once"
    assert modes_passed[0] == mode, f"Mode should be {mode}"
