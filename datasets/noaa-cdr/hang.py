import time
import itertools
from noaa_cdr import SeaSurfaceTemperatureOptimumInterpolationCollection, StorageFactory
from pctasks.core.tokens import Tokens, StorageAccountTokens
from pctasks.core.models.tokens import ContainerTokens


def main():
    storage = StorageFactory(
        tokens=Tokens(
            tokens={
                "noaacdr": StorageAccountTokens(
                    containers={
                        "sea-surface-temp-optimum-interpolation": ContainerTokens(
                            token="?sv=2021-10-04&st=2023-04-27T15%3A45%3A02Z&se=2023-05-28T15%3A45%3A00Z&sr=c&sp=rl&sig=UVlzJVwrgeXv9ocO57gXGnbclQhx3Mimkgcqez9tkAQ%3D"
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
