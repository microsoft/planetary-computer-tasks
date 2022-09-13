The GOES-R Advanced Baseline Imager (ABI) L2 Cloud and Moisture Imagery product provides 16 reflective and emissive bands at high temporal cadence over the Western Hemisphere.

The GOES-R series is the latest in the Geostationary Operational Environmental Satellites (GOES) program, which has been operated in a collaborative effort by NOAA and NASA since 1975. The operational GOES-R Satellites, GOES-16 (or GOES East) and GOES-17 (or GOES West), capture 16-band imagery from geostationary orbits over the Western Hemisphere via the Advance Baseline Imager (ABI) radiometer. The ABI captures 2 visible, 4 near-infrared, and 10 infrared channels at resolutions between 0.5km and 2km.

### Geographic coverage

The ABI captures three levels of coverage, each at a different temporal cadence depending on the modes described below. The goegraphic coverage for each image is described by the `goes:image-type` STAC Item property.

- _FULL DISK_: a circular image depicting nearly full coverage of the Western Hemisphere.
- _CONUS_: a 3,000 (lat) by 5,000 (lon) km rectangular image depicting the Continental U.S. (GOES-16) or the Pacific Ocean including Hawaii (GOES-17).
- _MESOSCALE_: a 1,000 by 1,000 km rectangular image. GOES-16 and 17 both alternate between two different mesoscale geographic regions.

### Modes

There are three standard scanning modes for the ABI instrument: Mode 3, Mode 4, and Mode 6.

- Mode _3_ consists of one observation of the full disk scene of the Earth, three observations of the continental United States (CONUS), and thirty observations for each of two distinct mesoscale views every fifteen minutes.
- Mode _4_ consists of the observation of the full disk scene every five minutes.
- Mode _6_ consists of one observation of the full disk scene of the Earth, two observations of the continental United States (CONUS), and twenty observations for each of two distinct mesoscale views every ten minutes.

The mode that each image was captured with is described by the `goes:mode` STAC Item property.

See this [ABI Scan Mode Demonstration](https://youtu.be/_c5H6R-M0s8) video for an idea of how the ABI scans multiple geographic regions over time.

### Cloud and Moisture Imagery

The Cloud and Moisture Imagery product contains one or more images with pixel values identifying "brightness values" that are scaled to support visual analysis.  Cloud and Moisture Imagery product (CMIP) files are generated for each of the sixteen ABI reflective and emissive bands. In addition, there is a multi-band product file that includes the imagery at all bands (MCMIP).

The Planetary Computer STAC Collection `goes-cmi` captures both the CMIP and MCMIP product files into individual STAC Items for each observation from a GOES-R satellite. It contains the original CMIP and MCMIP NetCDF files, as well as cloud-optimized GeoTIFF (COG) exports of the data from each MCMIP band (2km); the full-resolution CMIP band for bands 1, 2, 3, and 5; and a Web Mercator COG of bands 1, 2 and 3, which are useful for rendering.

This product is not in a standard coordinate reference system (CRS), which can cause issues with some tooling that does not handle non-standard large geographic regions.

### For more information
- [Beginner’s Guide to GOES-R Series Data](https://www.goes-r.gov/downloads/resources/documents/Beginners_Guide_to_GOES-R_Series_Data.pdf)
- [GOES-R Series Product Definition and Users’ Guide: Volume 5 (Level 2A+ Products)](https://www.goes-r.gov/products/docs/PUG-L2+-vol5.pdf) ([Spanish verison](https://github.com/NOAA-Big-Data-Program/bdp-data-docs/raw/main/GOES/QuickGuides/Spanish/Guia%20introductoria%20para%20datos%20de%20la%20serie%20GOES-R%20V1.1%20FINAL2%20-%20Copy.pdf))

