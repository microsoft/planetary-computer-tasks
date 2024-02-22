# USGS Lidar
Point cloud dataset converted to cloud optimized geotiffs.
There are reported data quality issues with this dataset, specifically regarding the spatial extent of STAC items disagreeing with the COG items.
This folder contains some of the analysis tools to understand this issue.

## Auditing Datasets
The workflow code in `lidar_audit.py` compares the spatial extent of the STAC items and their COG using a Jaccard similarity.
To submit this workflow, you can run:
```
pctasks workflow upsert-and-submit workflow.yaml -a parquet_prefix "items/3dep-lidar-hag.parquet" -a registry pccomponentstest.azurecr.io
```

This will write CSV files to `blob://usgslidareuwest/usgs-lidar-etl-data/{parquet_name}` with the similarity data.
Download the blobs into a directory and run `concatenate_csvs.py` to combine them.
For analysis you can then run:

```python
import pandas as pd

df = pd.read_csv("combined.csv")
df["error"] = df["similarity"] < 0.95 # True == error
df["state"] = df["3dep:usgs_id"].apply(lambda x: x.split("_")[2 if "USGS_LPC" in x else 0])
df.groupby("state").error.mean().sort_values()
```

This will the disagreement rate by state.