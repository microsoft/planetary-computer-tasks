# Note you will have to run this with `python -m pytest` from the datasets/aster directory

from pathlib import Path

import aster
import geopandas
import orjson


def test_update_geometries_from_dataframe() -> None:
    path = Path(__file__).parent / "data-files" / "aster-l1t-subset.parquet"
    dataframe = geopandas.read_parquet(path)
    item = next(aster.update_geometries_from_dataframe(dataframe))
    _ = orjson.dumps(item).decode("utf-8")
