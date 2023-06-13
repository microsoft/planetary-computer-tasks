# planetary-computer-tasks dataset: sentinel-1-rtc

Sentinel-1 RTC

## Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-1-rtc:latest -t pctasks-sentinel-1-rtc:{date}.{count} -f datasets/sentinel-1-rtc/Dockerfile .
```

## Notes

- Requires `--arg extra-prefix {year}`