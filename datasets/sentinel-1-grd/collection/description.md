The [Sentinel-1](https://sentinel.esa.int/web/sentinel/missions/sentinel-1) mission is a constellation of two polar-orbiting satellites, operating day and night performing C-band synthetic aperture radar imaging. The Level-1 Ground Range Detected (GRD) products in this Collection consist of focused SAR data that has been detected, multi-looked and projected to ground range using the Earth ellipsoid model WGS84. The ellipsoid projection of the GRD products is corrected using the terrain height specified in the product general annotation. The terrain height used varies in azimuth but is constant in range (but can be different for each IW/EW sub-swath).

Ground range coordinates are the slant range coordinates projected onto the ellipsoid of the Earth. Pixel values represent detected amplitude. Phase information is lost. The resulting product has approximately square resolution pixels and square pixel spacing with reduced speckle at a cost of reduced spatial resolution.

For the IW and EW GRD products, multi-looking is performed on each burst individually. All bursts in all sub-swaths are then seamlessly merged to form a single, contiguous, ground range, detected image per polarization.

For more information see the [ESA documentation](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/product-types-processing-levels/level-1)

### Terrain Correction

Users might want to geometrically or radiometrically terrain correct the Sentinel-1 GRD data from this collection. The [Sentinel-1-RTC Collection](https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc) collection is a global radiometrically terrain corrected dataset derived from Sentinel-1 GRD. Additionally, users can terrain-correct on the fly using [any DEM available on the Planetary Computer](https://planetarycomputer.microsoft.com/catalog?tags=DEM). See [Customizable radiometric terrain correction](https://planetarycomputer.microsoft.com/docs/tutorials/customizable-rtc-sentinel1/) for more.