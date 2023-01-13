# run this with `python -m pytest` from the datasets/usgs-lcmap/fix_items directory

from pathlib import Path
import json

from fix_items import remove_classes


def test_fix_ndjson_classes() -> None:
    path = Path(__file__).parent / "data-files" / "items.ndjson"
    with open(path, "r") as fobj:
        item = json.loads(fobj.readline())
        corrected_item = remove_classes(item)
        assert len(corrected_item["assets"]["lcpri"]["classification:classes"]) == 9
        assert len(corrected_item["assets"]["lcsec"]["classification:classes"]) == 9
        for c in corrected_item["assets"]["lcsec"]["classification:classes"]:
            assert c["value"] < 9
            assert "_to_" not in c["name"]
