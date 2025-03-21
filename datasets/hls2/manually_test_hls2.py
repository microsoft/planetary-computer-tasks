import hls2
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens
from pctasks.core.models.tokens import StorageAccountTokens, ContainerTokens
import os

test_storage_account = "marcdeltaresfloodssa"
test_container = "hls2"

tokens = Tokens(
    {
        test_storage_account: StorageAccountTokens(
            containers={
                test_container: ContainerTokens(token=os.environ["MARC_TEMP_SAS_TOKEN"]), }
        )
    }
)

def test_hls2():
    asset_uri = f"blob://{test_storage_account}/{test_container}/S30/56/P/PQ/2024/01/05/HLS.S30.T56PPQ.2024005T001421.v2.0/HLS.S30.T56PPQ.2024005T001421.v2.0.jpg"  # noqa: E501
    result = hls2.HLS2Collection.create_item(asset_uri, StorageFactory(tokens=tokens), upload=False)
    assert result
    item, = result
    assert item
    assert item.assets["B01"].href == f'https://{test_storage_account}.blob.core.windows.net/{test_container}/S30/56/P/PQ/2024/01/05/HLS.S30.T56PPQ.2024005T001421.v2.0/HLS.S30.T56PPQ.2024005T001421.v2.0.B01.tif'  # noqa: E501
    assert len(item.stac_extensions) == 4
    assert item.properties["platform"] == "sentinel-2a"
    assert len(item.assets) == 19 # 18 bands and 1 thumbnail
    assert "thumbnail" in item.assets

if __name__ == "__main__":
    test_hls2()