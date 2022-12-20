# Note you will have to run this with `python -m pytest` from the datasets/aster directory

from pathlib import Path

import aster
import orjson


def test_update_geometries_from_dataframe() -> None:
    path = Path(__file__).parent / "data-files" / "aster-l1t-subset.parquet"
    item_collection = aster.read_item_collection(path)
    item = aster.sign_and_update(item_collection.items[0], 0.001)
    _ = orjson.dumps(aster.fix_dict(item.to_dict(include_self_link=False))).decode(
        "utf-8"
    )
