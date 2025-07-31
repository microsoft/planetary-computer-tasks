import pathlib
import pystac

import logging
import s1grd
from stactools.sentinel1.metadata_links import MetadataLinks
from pctasks.core.storage import StorageFactory
import pytest


HERE = pathlib.Path(__file__).parent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
    logger.addHandler(handler)


@pytest.mark.parametrize(
    "item_id, annotation_name, expected_key",
    [
        (
            "S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1",
            "s1a-iw-grd-vh-20230628t210705-20230628t210730-049191-05ea4d-002",
            "vh",
        ),
        (
            "S1C_IW_GRDH_1SDV_20250708T025935_20250708T030005_003123_00655C_BA99",
            "s1c-iw-grd-vh-20250708t025935-20250708t030005-003123-00655c-002",
            "vh",
        ),
    ],
)
def test_metadata_links_annotation_pattern_parametrized(
    tmp_path, item_id: str, annotation_name: str, expected_key: str
):
    # Setup: create a minimal manifest.safe with dataObjectSection and fileLocation
    archive_dir = tmp_path / item_id
    annotation_filename = f"{annotation_name}.xml"
    annotation_dir = archive_dir / "annotation"
    annotation_dir.mkdir(parents=True)
    annotation_file = annotation_dir / annotation_filename
    annotation_file.write_text("<xml></xml>")

    # The manifest must reference the annotation file
    manifest_content = f"""
    <manifest>
      <dataObjectSection>
        <dataObject>
          <byteStream>
            <fileLocation href="annotation/{annotation_filename}"/>
          </byteStream>
        </dataObject>
      </dataObjectSection>
    </manifest>
    """
    manifest_file = archive_dir / "manifest.safe"
    manifest_file.write_text(manifest_content)
    try:
        logger.info(f"Creating MetadataLinks for {archive_dir}")
        ml = MetadataLinks(str(archive_dir))
        annotation_hrefs = ml.annotation_hrefs
        logger.info(f"Annotation hrefs: {annotation_hrefs}")
    except Exception as e:
        assert False, f"MetadataLinks failed: {e}"

    assert any(
        expected_key in key and annotation_file.name in href
        for key, href in annotation_hrefs
    )


def test_get_item_storage():
    asset_uri = "blob://sentinel1euwest/s1-grd/GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665_5673/manifest.safe"  # noqa: E501
    storage_factory = StorageFactory()
    storage, path = s1grd.get_item_storage(asset_uri, storage_factory=storage_factory)
    assert (
        path
        == "GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665.json"
    )  # noqa: E501
    assert storage.root_uri == "blob://sentinel1euwest/s1-grd-stac"


def test_rewrite_asset_hrefs():
    archive_storage = StorageFactory().get_storage(
        "blob://sentinel1euwest/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1"  # noqa: E501
    )

    item = pystac.Item.from_file(str(HERE / "test-data/sentinel-1-grd-item-raw.json"))
    result = {
        k: v.href
        for k, v in s1grd.rewrite_asset_hrefs(
            item,
            archive_storage,
            "/tmp/tmpsskmzq08/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1",
        ).assets.items()
    }

    expected = {
        "safe-manifest": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/manifest.safe",
        "schema-product-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/rfi-iw-vh.xml",
        "schema-product-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/rfi/rfi-iw-vv.xml",
        "schema-calibration-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/calibration-iw-vh.xml",
        "schema-calibration-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/calibration-iw-vv.xml",
        "schema-noise-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/noise-iw-vh.xml",
        "schema-noise-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/noise-iw-vv.xml",
        "thumbnail": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/preview/quick-look.png",
        "vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/measurement/iw-vh.tiff",
        "vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/measurement/iw-vv.tiff",
    }
    assert result == expected
