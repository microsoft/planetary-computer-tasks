This COG type is generated using the Z dimension of the [COPC data](https://planetarycomputer.microsoft.com/dataset/3dep-lidar-copc) data and removes noise, water, and using [`pdal.filters.smrf`](https://pdal.io/stages/filters.smrf.html#filters-smrf) followed by [pdal.filters.hag_nn](https://pdal.io/stages/filters.hag_nn.html#filters-hag-nn).

The Height Above Ground Nearest Neighbor filter takes as input a point cloud with Classification set to 2 for ground points. It creates a new dimension, HeightAboveGround, that contains the normalized height values.

Ground points may be generated with [`pdal.filters.pmf`](https://pdal.io/stages/filters.pmf.html#filters-pmf) or [`pdal.filters.smrf`](https://pdal.io/stages/filters.smrf.html#filters-smrf), but you can use any method you choose, as long as the ground returns are marked.

Normalized heights are a commonly used attribute of point cloud data. This can also be referred to as height above ground (HAG) or above ground level (AGL) heights. In the end, it is simply a measure of a point's relative height as opposed to its raw elevation value.

The filter finds the number of ground points nearest to the non-ground point under consideration. It calculates an average ground height weighted by the distance of each ground point from the non-ground point. The HeightAboveGround is the difference between the Z value of the non-ground point and the interpolated ground height.
