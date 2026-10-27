from datetime import datetime
from pathlib import Path

import numpy as np
import pystac
import pytest
import rasterio
from affine import Affine
from rasterio.crs import CRS

import modis

# MODIS sinusoidal grid: tile h23v07 at 500 m.
SINUSOIDAL = CRS.from_proj4("+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs")
PIXEL = 463.3127165275
ORIGIN = (5559752.598333, 2223901.039333)
SHAPE = (2400, 2400)


@pytest.fixture
def subdataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A GeoTIFF on the MODIS grid standing in for the HDF's first subdataset."""
    path = str(tmp_path / "subdataset.tif")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=SHAPE[1],
        height=SHAPE[0],
        count=1,
        dtype="uint8",
        crs=SINUSOIDAL,
        transform=Affine(PIXEL, 0.0, ORIGIN[0], 0.0, -PIXEL, ORIGIN[1]),
    ) as dataset:
        dataset.write(np.zeros((1, *SHAPE), dtype="uint8"))
    monkeypatch.setattr(modis.stactools.modis.utils, "subdatasets", lambda href: [path])
    return path


def test_add_projection_reads_the_hdf_grid(subdataset: str) -> None:
    item = pystac.Item("MOD10A1.A2000057.h23v07.061.2020037182526", None, None, datetime(2000, 2, 26), {})

    modis.add_projection(item, "MOD10A1.A2000057.h23v07.061.2020037182526.hdf")

    projection = pystac.extensions.projection.ProjectionExtension.ext(item)
    assert projection.has_extension(item)
    assert projection.epsg is None
    assert projection.wkt2.startswith("PROJCRS[")
    assert CRS.from_wkt(projection.wkt2) == SINUSOIDAL
    assert projection.shape == list(SHAPE)
    assert projection.transform == pytest.approx([PIXEL, 0.0, ORIGIN[0], 0.0, -PIXEL, ORIGIN[1]])
    min_x, max_y = ORIGIN
    max_x, min_y = min_x + PIXEL * SHAPE[1], max_y - PIXEL * SHAPE[0]
    ring = [coordinate for point in projection.geometry["coordinates"][0] for coordinate in point]
    assert ring == pytest.approx([max_x, min_y, max_x, max_y, min_x, max_y, min_x, min_y, max_x, min_y])


def test_add_projection_requires_subdatasets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modis.stactools.modis.utils, "subdatasets", lambda href: [])
    item = pystac.Item("item", None, None, datetime(2000, 2, 26), {})

    with pytest.raises(ValueError, match="No subdatasets"):
        modis.add_projection(item, "empty.hdf")
