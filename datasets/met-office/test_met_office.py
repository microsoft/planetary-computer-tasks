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
test_container = "staging"


@pytest.mark.parametrize(
    "asset_uri,collection_class",
    [
        (
            f"blob://{test_storage_account}/{test_container}/global/height/20251205T1200Z/20251208T0000Z-PT0060H00M.updated",
            MetOfficeGlobalHeightCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/near-surface/20251205T1200Z/20251207T0800Z-PT0044H00M.updated",
            MetOfficeGlobalNearSurfaceCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/pressure/20251205T1200Z/20251207T0400Z-PT0040H00M.updated",
            MetOfficeGlobalPressureCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/whole-atmosphere/20251205T1200Z/20251207T0500Z-PT0041H00M.updated",
            MetOfficeGlobalWholeAtmosphereCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/height/20251205T1500Z/20251205T1500Z-PT0000H00M.updated",
            MetOfficeUkHeightCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/near-surface/20251205T1500Z/20251205T1500Z-PT0000H00M.updated",
            MetOfficeUkNearSurfaceCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/pressure/20251205T1500Z/20251205T1500Z-PT0000H00M.updated",
            MetOfficeUkPressureCollection,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/whole-atmosphere/20251205T1500Z/20251205T1500Z-PT0000H00M.updated",
            MetOfficeUkWholeAtmosphereCollection,
        ),
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
