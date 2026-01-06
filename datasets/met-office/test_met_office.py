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
from stactools.met_office_deterministic.constants import Model, Theme

test_storage_account = "ukmoeuwest"
test_container = "staging"


@pytest.mark.parametrize(
    "asset_uri,collection_class,expected_model,expected_theme",
    [
        (
            f"blob://{test_storage_account}/{test_container}/global/height/20250106T0000Z.updated",
            MetOfficeGlobalHeightCollection,
            Model.global_,
            Theme.height,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/near-surface/20250106T0000Z.updated",
            MetOfficeGlobalNearSurfaceCollection,
            Model.global_,
            Theme.near_surface,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/pressure/20250106T0000Z.updated",
            MetOfficeGlobalPressureCollection,
            Model.global_,
            Theme.pressure_level,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/global/whole-atmosphere/20250106T0000Z.updated",
            MetOfficeGlobalWholeAtmosphereCollection,
            Model.global_,
            Theme.whole_atmosphere,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/height/20250106T0000Z.updated",
            MetOfficeUkHeightCollection,
            Model.uk,
            Theme.height,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/near-surface/20250106T0000Z.updated",
            MetOfficeUkNearSurfaceCollection,
            Model.uk,
            Theme.near_surface,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/pressure/20250106T0000Z.updated",
            MetOfficeUkPressureCollection,
            Model.uk,
            Theme.pressure_level,
        ),
        (
            f"blob://{test_storage_account}/{test_container}/uk/whole-atmosphere/20250106T0000Z.updated",
            MetOfficeUkWholeAtmosphereCollection,
            Model.uk,
            Theme.whole_atmosphere,
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
