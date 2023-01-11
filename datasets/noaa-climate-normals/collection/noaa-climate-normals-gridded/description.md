The [NOAA Gridded United States Climate Normals](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals#tab-1027) provide a continuous grid of temperature and precipitation data across the contiguous United States (CONUS). The grids are derived from NOAA's [NClimGrid dataset](https://planetarycomputer.microsoft.com/dataset/group/noaa-nclimgrid), and resolutions (nominal 5x5 kilometer) and spatial extents (CONUS) therefore match that of NClimGrid. Monthly, seasonal, and annual gridded normals are computed from simple averages of the NClimGrid data and are provided for three time-periods: 1901–2020, 1991–2020, and 2006–2020. Daily gridded normals are smoothed for a smooth transition from one day to another and are provided for two time-periods: 1991–2020, and 2006–2020.

NOAA produces Climate Normals in accordance with the [World Meteorological Organization](https://public.wmo.int/en) (WMO), of which the United States is a member. The WMO requires each member nation to compute 30-year meteorological quantity averages at least every 30 years, and recommends an update each decade, in part to incorporate newer weather stations. The 1991–2020 U.S. Climate Normals are the latest in a series of decadal normals first produced in the 1950s. 

The data in this Collection have been converted from the original NetCDF format to Cloud Optimized GeoTIFFs (COGs). This Collection contains gridded data for the following frequencies and time periods:

- Annual, seasonal, and monthly normals
    - 100-year (1901–2000)
    - 30-year (1991–2020)
    - 15-year (2006–2020)
- Daily normals
    - 30-year (1991–2020)
    - 15-year (2006–2020)

## STAC Metadata

The STAC items in this collection contain several custom fields that can be used to further filter the data.

* `noaa_climate_normals:period`: Climate normal time period. This can be "1901-2000", "1991-2020", or "2006-2020".
* `noaa_climate_normals:frequency`: Climate normal temporal interval (frequency). This can be "daily", "monthly", "seasonal" , or "annual"
* `noaa-climate_normals:time_index`: Time step index, e.g., month of year (1-12).

The `description` field of the assets varies by frequency. Using `prcp_norm` as an example, the descriptions are

* annual: "Annual precipitation normals from monthly precipitation normal values"
* seasonal: "Seasonal precipitation normals (WSSF) from monthly normals"
* monthly: "Monthly precipitation normals from monthly precipitation values"
* daily: "Precipitation normals from daily averages"

Check the assets on individual items for the appropriate description.

The STAC keys for most assets consist of two abbreviations. A "variable":


| Abbreviation |               Description                |
| ------------ | ---------------------------------------- |
| prcp         | Precipitation over the time period       |
| tavg         | Mean temperature over the time period    |
| tmax         | Maximum temperature over the time period |
| tmin         | Minimum temperature over the time period |

And an "aggregation"

| Abbreviation |                                  Description                                   |
| ------------ | ------------------------------------------------------------------------------ |
| max          | Maximum of the variable over the time period                                   |
| min          | Minimum of the variable over the time period                                   |
| std          | Standard deviation of the value over the time period                           |
| flag         | An count of the number of inputs (months, years, etc.) to calculate the normal |
| norm         | The normal for the variable over the time period                               |

So, for example, `prcp_max` for monthly data is the "Maximum values of all input monthly precipitation normal values".