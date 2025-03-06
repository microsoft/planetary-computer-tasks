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
    item, = result
    print(item.assets['B01'].to_dict())
    # assert item.assets["so2"].href == "https://sentinel5euwest.blob.core.windows.net/sentinel-5p/TROPOMI/L2__SO2___/2023/06/30/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605.nc"  # noqa: E501

if __name__ == "__main__":
    test_hls2()