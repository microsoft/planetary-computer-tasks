import pytest
from met_office import (
    MetOfficeCollection,
    MetOfficeGlobalHeightCollection,
    MetOfficeGlobalNearSurfaceCollection,
    MetOfficeGlobalPressureCollection,
    MetOfficeGlobalWholeAtmosphereCollection,
    MetOfficeUkHeightCollection,
    MetOfficeUkNearSurfaceCollection,
    MetOfficeUkPressureCollection,
    MetOfficeUkWholeAtmosphereCollection,
)
from pctasks.core.storage import StorageFactory

test_storage_account = "ukmoeuwest"
test_container = "deterministic"


@pytest.mark.parametrize(
    "asset_uri,collection_class",
    [
        (
            f"blob://{test_storage_account}/{test_container}/global/height/update/2026/01/06/1200Z/20260113T1200Z-PT0168H00M.updated",
            MetOfficeGlobalHeightCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/near-surface/update/2026/01/06/1200Z/20260113T1200Z-PT0168H00M.updated",
            MetOfficeGlobalNearSurfaceCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/pressure/update/2026/01/06/1200Z/20260113T1200Z-PT0168H00M.updated",
            MetOfficeGlobalPressureCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/whole-atmosphere/update/2026/01/06/1200Z/20260113T1200Z-PT0168H00M.updated",
            MetOfficeGlobalWholeAtmosphereCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/height/update/2024/06/26/0700Z/20240626T1900Z-PT0012H00M.updated",
            MetOfficeUkHeightCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/near-surface/update/2024/11/29/0600Z/20241201T1200Z-PT0054H00M.updated",
            MetOfficeUkNearSurfaceCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/pressure/update/2024/10/25/1700Z/20241026T0500Z-PT0012H00M.updated",
            MetOfficeUkPressureCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/whole-atmosphere/update/2024/12/13/1100Z/20241213T2300Z-PT0012H00M.updated",
            MetOfficeUkWholeAtmosphereCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/near-surface/update/2025/12/30/1200Z/20251230T1200Z-PT0000H00M.updated",
            MetOfficeGlobalNearSurfaceCollection,
        )
    ],
)
def test_met_office_collection(
    asset_uri: str,
    collection_class: type[MetOfficeCollection],
) -> None:
    class MockBlobClient:
        def __init__(self, real_client):
            self._real_client = real_client

        def delete_file(self, path):
            # Mock delete to avoid modifying storage
            pass

        def __getattr__(self, name):
            # Delegate all other methods to the real client
            return getattr(self._real_client, name)

    class MockStorageFactory:
        def __init__(self, real_factory):
            self._real_factory = real_factory

        def get_storage(self, uri):
            # Use real storage for reading
            return self._real_factory.get_storage(uri)

        def get_storage_for_file(self, uri):
            # Wrap the real client with our mock to intercept delete
            real_client, path = self._real_factory.get_storage_for_file(uri)
            return MockBlobClient(real_client), path

    real_storage_factory = StorageFactory()
    storage_factory = MockStorageFactory(real_storage_factory)
    result = collection_class.create_item(asset_uri, storage_factory)  # pyright: ignore[reportArgumentType]

    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    result[0].validate()
