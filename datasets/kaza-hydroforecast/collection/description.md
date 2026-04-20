This dataset is a daily updated set of HydroForecast seasonal river flow forecasts at six locations in the Kwando and Upper Zambezi river basins. More details about the locations, project context, and to interactively view current and previous forecasts, visit our [public website](https://dashboard.hydroforecast.com/public/wwf-kaza).

## Flow forecast dataset and model description

[HydroForecast](https://www.upstream.tech/hydroforecast) is a theory-guided machine learning hydrologic model that predicts streamflow in basins across the world. For the Kwando and Upper Zambezi, HydroForecast makes daily predictions of streamflow rates using a [seasonal analog approach](https://support.upstream.tech/article/125-seasonal-analog-model-a-technical-overview). The model's output is probabilistic and the mean, median and a range of quantiles are available at each forecast step.

The underlying model has the following attributes: 

* Timestep: 10 days
* Horizon: 10 to 180 days 
* Update frequency: daily
* Units: cubic meters per second (m³/s)
    
## Site details

The model produces output for six locations in the Kwando and Upper Zambezi river basins.

* Upper Zambezi sites
    * Zambezi at Chavuma
    * Luanginga at Kalabo
* Kwando basin sites
    * Kwando at Kongola -- total basin flows
    * Kwando Sub-basin 1
    * Kwando Sub-basin 2 
    * Kwando Sub-basin 3
    * Kwando Sub-basin 4
    * Kwando Kongola Sub-basin

## STAC metadata

There is one STAC item per location. Each STAC item has a single asset linking to a Parquet file in Azure Blob Storage.