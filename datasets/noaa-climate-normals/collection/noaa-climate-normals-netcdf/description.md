The [NOAA Gridded United States Climate Normals](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals#tab-1027) provide a continuous grid of temperature and precipitation data across the contiguous United States (CONUS). The grids are derived from NOAA's [NClimGrid dataset](https://planetarycomputer.microsoft.com/dataset/group/noaa-nclimgrid), and resolutions (nominal 5x5 kilometer) and spatial extents (CONUS) therefore match that of NClimGrid. Monthly, seasonal, and annual gridded normals are computed from simple averages of the NClimGrid data and are provided for three time-periods: 1901–2020, 1991–2020, and 2006–2020. Daily gridded normals are smoothed for a smooth transition from one day to another and are provided for two time-periods: 1991–2020, and 2006–2020.

NOAA produces Climate Normals in accordance with the [World Meteorological Organization](https://public.wmo.int/en) (WMO), of which the United States is a member. The WMO requires each member nation to compute 30-year meteorological quantity averages at least every 30 years, and recommends an update each decade, in part to incorporate newer weather stations. The 1991–2020 U.S. Climate Normals are the latest in a series of decadal normals first produced in the 1950s. 

The data in this Collection are the original NetCDF files provided by NOAA's National Centers for Environmental Information. This Collection contains gridded data for the following frequencies and time periods:

- Annual, seasonal, and monthly normals
    - 100-year (1901–2000)
    - 30-year (1991–2020)
    - 15-year (2006–2020)
- Daily normals
    - 30-year (1991–2020)
    - 15-year (2006–2020)

For most use-cases, we recommend using the [`noaa-climate-normals-gridded`](https://planetarycomputer.microsoft.com/dataset/noaa-climate-normals-gridded) collection, which contains the same data in Cloud Optimized GeoTIFF format. The NetCDF files are delivered to Azure as part of the [NOAA Open Data Dissemination (NODD) Program](https://www.noaa.gov/information-technology/open-data-dissemination).
