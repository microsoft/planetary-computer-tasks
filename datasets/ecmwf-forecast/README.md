# ECMWF Forecast

## Chunks

- Asset chunk creation takes 5-10 minutes when passing a `--since {date}` argument.
- There are about 950 `grib2` files generated each day.
- Item creation is fast (the data is not touched), so a single chunk file for daily data is fine — no need to limit `chunk_length`.

## Dockerfile

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-ecmwf-forecast:latest -t pctasks-ecmwf-forecast:{date}.{count} -f datasets/ecmwf-forecast/Dockerfile .
```
