ECMWF Open Data real-time forecasts from the Integrated Forecasting System (IFS) at 0.1-degree resolution. This collection contains assets under the `ifs/0p1/` source path. The `ecmwf-forecast` collection remains the destination for 0.25-degree and legacy 0.4-degree forecasts.

The data are provided as GRIB2 files with accompanying index files for accessing individual messages. Each STAC item represents a global GRIB2 file. Item properties include `ecmwf:resolution` (`0.10`), `ecmwf:stream`, `ecmwf:type`, `ecmwf:reference_datetime`, and `ecmwf:forecast_datetime`.

See the [ECMWF Open Data documentation](https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time) for product details, availability, and usage guidance.

Data are provided by the [European Centre for Medium-Range Weather Forecasts](https://www.ecmwf.int/) under the [Creative Commons Attribution 4.0 International license](https://creativecommons.org/licenses/by/4.0/). Users must follow the [ECMWF attribution and terms of use](https://apps.ecmwf.int/datasets/licences/general/).
