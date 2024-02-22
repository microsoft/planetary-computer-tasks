import time
import itertools
import os
from noaa_cdr import SeaSurfaceTemperatureOptimumInterpolationCollection, StorageFactory
from pctasks.core.tokens import Tokens, StorageAccountTokens
from pctasks.core.models.tokens import ContainerTokens


def main() -> None:
    storage = StorageFactory(
        tokens=Tokens(
            tokens={
                "noaacdr": StorageAccountTokens(
                    containers={
                        "sea-surface-temp-optimum-interpolation": ContainerTokens(
                            token=os.environ["NOAA_CDR_STORAGE_TOKEN"]
                        )
                    }
                )
            }
        )
    )
    href = "blob://noaacdr/sea-surface-temp-optimum-interpolation/data/v2.1/avhrr/199510/oisst-avhrr-v02r01.19951031.nc"
    for i in itertools.count(1):
        t0 = time.time()
        SeaSurfaceTemperatureOptimumInterpolationCollection.create_item(href, storage)
        t1 = time.time()
        print(f"create_item [{i}]", round(t1 - t0, 2))


if __name__ == "__main__":
    main()
