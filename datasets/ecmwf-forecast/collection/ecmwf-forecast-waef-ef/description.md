The [ECMWF catalog of real-time products](https://www.ecmwf.int/en/forecasts/datasets/catalogue-ecmwf-real-time-products) offers real-time meterological and oceanographic productions from the ECMWF forecast system. Users should consult the [ECMWF Forecast User Guide](https://confluence.ecmwf.int/display/FUG/1+Introduction) for detailed information on each of the products.

## Overview of products

The following diagram shows the publishing schedule of the various products.

<a href="https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/ecmwf-forecast-coverage.png"><img src="https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/ecmwf-forecast-coverage.png" width="100%"/></a>

The vertical axis shows the various products, defined below, which are grouped by combinations of `stream`, `forecast type`, and `reference time`. The horizontal axis shows *forecast times* in 3-hour intervals out from the reference time. A black square over a particular forecast time, or step, indicates that a forecast is made for that forecast time, for that particular `stream`, `forecast type`, `reference time` combination.

* **stream** is the forecasting system that produced the data. The values in this STAC collection are:
  * `waef`: [ensemble forecast](https://confluence.ecmwf.int/display/FUG/ENS+-+Ensemble+Forecasts), ocean wave fields
* **type** is the forecast type. The values in this STAC collection are:
  * `ef`: ensemble forecast
* **reference time** is the hours after midnight when the model was run. Each stream / type will produce assets for different forecast times (steps from the reference datetime) depending on the reference time.

Visit the [ECMWF's User Guide](https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time) for more details on each of the various products.

Assets are available for the previous 30 days.

## Asset overview

The data are provided as [GRIB2 files](https://confluence.ecmwf.int/display/CKB/What+are+GRIB+files+and+how+can+I+read+them).
Additionally, [index files](https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time#ECMWFOpenDataRealTime-IndexFilesIndexfiles) are provided, which can be used to read subsets of the data from Azure Blob Storage.

Within each `stream`, `forecast type`, `reference time`, the structure of the data are mostly consistent. Each GRIB2 file will have the
same data variables, coordinates (aside from `time` as the *reference time* changes and `step` as the *forecast time* changes). The exception
is the `enfo-ep` and `waef-ep` products, which have more `step`s in the 240-hour forecast than in the 360-hour forecast. 

See the example notebook for more on how to access the data.

## STAC metadata

The Planetary Computer provides a single STAC item per GRIB2 file. Each GRIB2 file is global in extent, so every item has the same
`bbox` and `geometry`.

A few custom properties are available on each STAC item, which can be used in searches to narrow down the data to items of interest:

* `ecmwf:step`: The offset from the reference datetime, expressed as `<value><unit>`, for example `"3h"` means "3 hours from the reference datetime". 
* `ecmwf:reference_datetime`: The datetime when the model was run. This indicates when the forecast *was made*, rather than when it's valid for.
* `ecmwf:forecast_datetime`: The datetime for which the forecast is valid. This is also set as the item's `datetime`.

See the example notebook for more on how to use the STAC metadata to query for particular data.

## Attribution

The products listed and described on this page are available to the public and their use is governed by the [Creative Commons CC-4.0-BY license and the ECMWF Terms of Use](https://apps.ecmwf.int/datasets/licences/general/). This means that the data may be redistributed and used commercially, subject to appropriate attribution.

The following wording should be attached to the use of this ECMWF dataset: 

1. Copyright statement: Copyright "© [year] European Centre for Medium-Range Weather Forecasts (ECMWF)".
2. Source [www.ecmwf.int](http://www.ecmwf.int/)
3. License Statement: This data is published under a Creative Commons Attribution 4.0 International (CC BY 4.0). [https://creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/)
4. Disclaimer: ECMWF does not accept any liability whatsoever for any error or omission in the data, their availability, or for any loss or damage arising from their use.
5. Where applicable, an indication if the material has been modified and an indication of previous modifications.

The following wording shall be attached to services created with this ECMWF dataset:

1. Copyright statement: Copyright "This service is based on data and products of the European Centre for Medium-Range Weather Forecasts (ECMWF)".
2. Source www.ecmwf.int
3. License Statement: This ECMWF data is published under a Creative Commons Attribution 4.0 International (CC BY 4.0). [https://creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/)
4. Disclaimer: ECMWF does not accept any liability whatsoever for any error or omission in the data, their availability, or for any loss or damage arising from their use.
5. Where applicable, an indication if the material has been modified and an indication of previous modifications

## More information

For more, see the [ECMWF's User Guide](https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time) and [example notebooks](https://github.com/ecmwf/notebook-examples/tree/master/opencharts).