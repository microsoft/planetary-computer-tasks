import json
from pathlib import Path
from typing import Any

import pytest


REPOSITORY_ROOT = Path(__file__).parents[3]
COLLECTION_TEMPLATES = sorted(
    (REPOSITORY_ROOT / "datasets").glob("**/template.json")
)


@pytest.mark.parametrize(
    "template_path",
    COLLECTION_TEMPLATES,
    ids=lambda path: str(path.relative_to(REPOSITORY_ROOT / "datasets")),
)
def test_collection_has_geoparquet_asset(template_path: Path) -> None:
    collection: dict[str, Any] = json.loads(template_path.read_text())
    collection_id = collection["id"]
    asset = collection["assets"]["geoparquet-items"]

    assert asset["href"] == f"abfs://items/{collection_id}.parquet"
    assert asset["type"] == "application/x-parquet"
    assert asset["table:storage_options"]["account_name"] == "pcstacitems"
    assert "stac-items" in asset["roles"]
