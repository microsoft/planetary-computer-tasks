import sentinel_5p
import planetary_computer
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens
from pctasks.core.models.tokens import StorageAccountTokens, ContainerTokens


def test_sentinel_5p():
    asset_uri = "blob://sentinel5euwest/sentinel-5p/TROPOMI/L2__SO2___/2023/06/30/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605.nc"  # noqa: E501
    result = sentinel_5p.Sentinel5pNetCDFCollection.create_item(
        asset_uri,
        StorageFactory(
            tokens=Tokens(
                {
                    "sentinel5euwest": StorageAccountTokens(
                        containers={
                            "sentinel-5p": ContainerTokens(token=planetary_computer.sas.get_token("sentinel5euwest", "sentinel-5p").token)
                        }
                    )
                }

            )

        ),
    )
    item, = result
    assert item.assets["so2"].href == "https://sentinel5euwest.blob.core.windows.net/sentinel-5p/TROPOMI/L2__SO2___/2023/06/30/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605/S5P_NRTI_L2__SO2____20230630T182849_20230630T183349_29600_03_020401_20230630T190605.nc"  # noqa: E501