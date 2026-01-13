This collection offers 48 parameters at near-surface level from the Met Office global deterministic 10km forecast. This is a numerical weather prediction forecast for the whole globe, with a resolution of approximately 0.09 degrees i.e. 10km (2,560 x 1,920 grid points).

The data is available as NetCDF files. It's offered on a free, unsupported basis, so we don't recommend using it for any critical business purposes.

**Note: This dataset is not yet available in the Planetary Computer API, but can be accessed directly from Azure Blob Storage.**

## Data collection height
There are 3 forecast heights used within the near-surface this collection:
* Surface: the default collection height
* Screen level: 1.5m above the surface
* Wind parameters: 10m above the surface

## Timesteps
For most parameters, the following time steps are available, see exceptions below:
* every hour from 0 to 54 hours
* every 3 hours from 57 to 144 hours
* every 6 hours from 150 to 168 hours

Exceptions (for `accumulation`, `min`, `max` and `mean` parameters):
* Height of orography (height_of_orography) is only available at 0H
* Hourly latent heat flux at surface mean (latent_heat_flux_at_surface_mean-PT01H) is only available every hour from 1 to 54 hours
* 3H latent heat flux at surface mean (latent_heat_flux_at_surface_mean-PT03H) is only available every three hours from 57 to 144 hours
* 6H latent heat flux at surface mean (latent_heat_flux_at_surface_mean-PT06H) is only available every six hours from 150 to 168 hours
* Hourly precipitation accumulation (precipitation_accumulation-PT01H) is only available every hour from 1 to 48 hours
* 3H precipitation accumulation (precipitation_accumulation-PT03H) is only available every three hours from 51 to 144 hours
* 6H precipitation accumulation (precipitation_accumulation-PT06H) is only available every six hours from 150 to 168 hours
* Radiation flux in uv downward at surface (radiation_flux_in_uv_downward_at_surface) has three hourly timesteps from 0 to 144 hours
* Hourly rainfall accumulation (rainfall_accumulation-PT01H) is only available every hour from 1 to 54 hours
* 3H rainfall accumulation (rainfall_accumulation-PT03H) is only available every three hours from 57 to 144 hours
* 6H rainfall accumulation (rainfall_accumulation-PT06H) is only available every six hours from 150 to 168 hours 
* Hourly rainfall rate from convection max (rainfall_rate_from_convection_max-PT01H) is only available every hour from 1 to 54 hours
* 3H rainfall rate from convection max (rainfall_rate_from_convection_max-PT03H) is only available every three hours from 57 to 144 hours
* 6H rainfall rate from convection max (rainfall_rate_from_convection_max-PT06H) is only available every six hours from 150 to 168 hours
* Hourly snowfall rate from convection max (snowfall_rate_from_convection_max-PT01H) is only available every hour from 1 to 54 hours
* 3H snowfall rate from convection max (snowfall_rate_from_convection_max-PT03H) is only available every three hours from 57 to 144 hours
* 6H snowfall rate from convection max (snowfall_rate_from_convection_max-PT06H) is only available every six hours from 150 to 168 hours
* Hourly snowfall rate from convection mean (snowfall_rate_from_convection_mean-PT01H) is only available every hour from 1 to 54 hours
* 3H snowfall rate from convection mean (snowfall_rate_from_convection_mean-PT03H) is only available every three hours from 57 to 144 hours
* 6H snowfall rate from convection mean (snowfall_rate_from_convection_mean-PT06H) is only available every six hours from 150 to 168 hours
* Hourly temperature at screen level max (temperature_at_screen_level_max-PT01H) is only available every hour from 1 to 54 hours
* 3H temperature at screen level max (temperature_at_screen_level_max-PT03H) is only available every three hours from 57 to 144 hours
* 6H temperature at screen level max (temperature_at_screen_level_max-PT06H) is only available every six hours from 150 to 168 hours
* Hourly temperature at screen level min (temperature_at_screen_level_min-PT01H) is only available every hour from 1 to 54 hours
* 3H remperature at screen level min (temperature_at_screen_level_min-PT03H) is only available every three hours from 57 to 144 hours
* 6H temperature at screen level min (temperature_at_screen_level_min-PT06H) is only available every six hours from 150 to 168 hours
* Hourly wind gust at 10m max (wind_gust_at_10m_max-PT01H) is only available every hour from 1 to 54 hours 
* 3H wind gust at 10m max (wind_gust_at_10m_max-PT03H) is only available every three hours from 57 to 144 hours
* 6H wind gust at 10m max (wind_gust_at_10m_max-PT06H) is only available every six hours from 150 to 168 hours

## Update Frequency
The model is run four times each day, with forecast reference times of 00:00, 06:00, 12:00 and 18:00 (UTC).

The runs at 00:00 and 12:00 provide data for the next 168 hours. The runs at 06:00 and 18:00 provide data for the next 67 hours.

The forecast reference time represents the nominal data time or start time of a model forecast run, rather than the time when the data is available.

## Archive length and latency
As of December 2025, the archive contains data from December 2023 onwards. Forecasts will continue to be available for at least two years from their data date.

The data is typically available 6 hours after the model run time.

## Technical specs
The data is available as NetCDF files. NetCDF (Network Common Data Form) is an interface for array-orientated data access and a library that supports the interface. It is composed of 3 components:
* Variables store the data 
* Dimensions give relevant dimension information for the variables
* Attributes provide auxiliary information about the variables or dataset itself 

NetCDF is used within the atmospheric and oceanic science communities and is network transparent, allowing for it to be accessed by computers that store integers, characters and floating-point numbers.

Iris supports NetCDF files through reading, writing and handling. Iris implements a model based on the CF conventions, giving a format-agnostic interface for working with data.

[Find further support on using Iris with NetCDF files.](https://scitools-iris.readthedocs.io/en/stable/)

## Help us improve the data services we offer
[Join the Met Office research panel](https://forms.office.com/Pages/ResponsePage.aspx?id=YYHxF9cgRkeH_VD-PjtmGdxioYGoFbFIkZuB_q8Fb3VUQkoxRVQzTFdUMzNMVzczWVM5VTc3QTY3MC4u) to help us understand how people interact with weather and climate data, uncover challenges and explore opportunities.

## Data access

These files are available from the Azure Blob Storage account at https://ukmoeuwest.blob.core.windows.net. This storage account is in Azure's West Europe region. Users wishing to perform large-scale processing on the data should also locate their compute in Azure's West Europe region. All data files are in NetCDF format.

Within this account forecasts are organized by region, category, and runtime. Each file path within the container will start with:

deterministic/global/near-surface/YYYYMMDDTHHMMZ

Where YYYY is the 4-digit year, MM is the two-digit month, DD is the two-digit day, and HHMMZ is the UTC forecast runtime. Within that run's directory are NetCDF files for each of the variables produced by the forecast. For example:
https://ukmoeuwest.blob.core.windows.net/deterministic/global/near-surface/20250101T0000Z/20250101T0000Z-PT0000H00M-fog_fraction_at_screen_level.nc

Users must use a Shared Access Signature (SAS) token to authorize requests to Azure Blob Storage. Users may request a read-only SAS token for a specific asset URL using the following endpoint: https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={url}
For example:
https://planetarycomputer.microsoft.com/api/sas/v1/sign?href=https://ukmoeuwest.blob.core.windows.net/deterministic/global/near-surface/20250101T0000Z/20250101T0000Z-PT0000H00M-fog_fraction_at_screen_level.nc

Additionally, the Planetary Computer's SAS token endpoint allows for the generation of a read-only SAS token that grants access to all assets in the selected collection. For example, to receive a SAS token to access this collection please use:

https://planetarycomputer.microsoft.com/api/sas/v1/token/met-office-global-deterministic-near-surface

Users can use this token to connect to and read data from this container using Blobfuse2 (azure-storage-fuse).

## How to cite
Met Office global deterministic 10km forecast was accessed on DATE from the Microsoft Planetary Computer (https://zenodo.org/records/7261897).

## License
British Crown copyright 2023-2025, the Met Office, is licensed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/deed.en).

## Providers
[Met Office](https://www.metoffice.gov.uk/)
See all datasets managed by [Met Office.](https://registry.opendata.aws/?search=managedBy:met%20office)

## Contact
[servicedesk@metoffice.gov.uk](mailto:servicedesk@metoffice.gov.uk). Service desk is only available Mon – Fri, 09:00 until 17:00 UTC (-1 hour during BST). As a non-operational service we aim to respond to any service support enquiries within 3-5 business days.
