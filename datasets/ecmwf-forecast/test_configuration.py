import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from jinja2 import StrictUndefined, Template

DATASET_DIR = Path(__file__).parent


@pytest.fixture
def dataset() -> Dict[str, Any]:
    return yaml.safe_load((DATASET_DIR / "dataset.yaml").read_text())


@pytest.mark.parametrize(
    ("resolution", "expected"),
    [
        ("0p1", ["ecmwf-forecast-0p1"]),
        ("0p25", ["ecmwf-forecast"]),
        ("0p4-beta", ["ecmwf-forecast"]),
        ("0p10", []),
    ],
)
@pytest.mark.parametrize("stream", ["enfo", "oper", "waef", "wave", "scda"])
@pytest.mark.parametrize("model", ["ifs", "aifs"])
@pytest.mark.parametrize("suffix", ["", "-opendata"])
def test_resolution_routing(
    dataset: Dict[str, Any],
    resolution: str,
    expected: List[str],
    stream: str,
    model: str,
    suffix: str,
) -> None:
    path = (
        f"20261026/00z/{model}/{resolution}/{stream}{suffix}/"
        f"20261026000000-0h-{stream}-fc.grib2"
    )
    matched = []
    for collection in dataset["collections"]:
        storage = collection["asset_storage"][0]
        options = storage["chunks"]["options"]
        assert storage["uri"] == "blob://ai4edataeuwest/ecmwf/"
        assert options["match_full_path"] is True
        assert options["extensions"] == [".grib2"]
        if re.search(options["matches"], path):
            matched.append(collection["id"])
    assert matched == (expected if model == "ifs" and not suffix else [])


def test_collection_configuration(dataset: Dict[str, Any]) -> None:
    collections = dataset["collections"]
    assert [collection["id"] for collection in collections] == [
        "ecmwf-forecast",
        "ecmwf-forecast-0p1",
    ]
    assert len({c["chunk_storage"]["uri"] for c in collections}) == 2
    for collection in collections:
        assert collection["class"] == "ecmwf_forecast:EcmwfCollection"
        assert collection["asset_storage"][0]["chunks"]["splits"] == [
            {"depth": 1, "folder_matches": "^${{ args.year-prefix }}"}
        ]
        match = re.fullmatch(r"\$\{\{ local\.path\((.+)\) \}\}", collection["template"])
        assert match is not None
        template_dir = DATASET_DIR / match[1]
        description = (template_dir / "description.md").read_text()
        template = Template(
            (template_dir / "template.json").read_text(), undefined=StrictUndefined
        )
        body = json.loads(
            template.render(collection={"description": json.dumps(description)[1:-1]})
        )
        assert body["id"] == collection["id"]
        if collection["id"] == "ecmwf-forecast-0p1":
            assert body["summaries"]["ecmwf:resolution"] == ["0.10"]
            assert body["extent"]["spatial"]["bbox"] == [[-180, -90, 180, 90]]
            assert "geoparquet-items" not in body["assets"]


def test_streaming_configuration(dataset: Dict[str, Any]) -> None:
    workflow = yaml.safe_load((DATASET_DIR / "streaming.yaml").read_text())
    assert "collection_id" in workflow["args"]
    assert workflow["id"] == "${{ args.collection_id }}-streaming-test"
    task = workflow["jobs"]["create-items"]["tasks"][0]
    assert task["image"] == dataset["image"]
    assert task["args"]["collection_id"] == "${{ args.collection_id }}"
    assert task["args"]["streaming_options"]["queue_url"] == (
        "${{args.queue_account_url}}/${{ args.collection_id }}"
    )
