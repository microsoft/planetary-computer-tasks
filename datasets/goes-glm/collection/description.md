The [Geostationary Lightning Mapper (GLM)](https://www.goes-r.gov/spacesegment/glm.html) is a single-channel, near-infrared optical transient detector that can detect the momentary changes in an optical scene, indicating the presence of lightning. GLM measures total lightning (in-cloud, cloud-to-cloud and cloud-to-ground) activity continuously over the Americas and adjacent ocean regions with near-uniform spatial resolution of approximately 10 km. GLM collects information such as the frequency, location and extent of lightning discharges to identify intensifying thunderstorms and tropical cyclones. Trends in total lightning available from the GLM provide critical information to forecasters, allowing them to focus on developing severe storms much earlier and before these storms produce damaging winds, hail or even tornadoes.

The GLM data product consists of a hierarchy of earth-located lightning radiant energy measures including events, groups, and flashes:

- Lightning events are detected by the instrument.
- Lightning groups are a collection of one or more lightning events that satisfy temporal and spatial coincidence thresholds.
- Similarly, lightning flashes are a collection of one or more lightning groups that satisfy temporal and spatial coincidence thresholds.

The product includes the relationship among lightning events, groups, and flashes, and the area coverage of lightning groups and flashes. The product also includes processing and data quality metadata, and satellite state and location information. 

The GLM dataset is available in the original (source) NetCDF and derived [GeoParquet](https://github.com/opengeospatial/geoparquet) formats.