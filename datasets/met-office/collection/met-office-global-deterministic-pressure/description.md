This collection offers 8 parameters at 33 available pressure levels (from 100000Pa to 1000Pa) from the Met Office global deterministic 10km forecast. This is a numerical weather prediction forecast for the whole globe, with a resolution of approximately 0.09 degrees i.e. 10km (2,560 x 1,920 grid points).

The data is available as NetCDF files. It's offered on a free, unsupported basis, so we don’t recommend using it for any critical business purposes.

## Pressure Levels
Available pressure levels, in Pascals (Pa), are:
* 100000.0 97500.0 95000.0 92500.0 90000.0 85000.0 80000.0 75000.0 70000.0 65000.0 60000.0 55000.0 50000.0 45000.0 40000.0 37500.0 35000.0 32500.0 30000.0 27500.0 25000.0 22500.0 20000.0 17500.0 15000.0 12500.0 10000.0 7000.0 5000.0 4000.0 3000.0 2000.0 1000.0

## Timesteps
The following timesteps are available:
* every hour from 0 to 54 hours (for most parameters, see parameter table for exceptions)
* every 3 hours from 57 to 144 hours
* every 6 hours from 150 to 168 hours

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

deterministic/global/pressure/YYYYMMDDTHHMMZ

Where YYYY is the 4-digit year, MM is the two-digit month, DD is the two-digit day, and HHMMZ is the UTC forecast runtime. Within that run's directory are NetCDF files for each of the variables produced by the forecast. For example:
https://ukmoeuwest.blob.core.windows.net/deterministic/global/pressure/20260101T0000Z/20260101T0000Z-PT0000H00M-temperature.nc

Users must use a Shared Access Signature (SAS) token to authorize requests to Azure Blob Storage. Users may request a read-only SAS token for a specific asset URL using the following endpoint: https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={url}
For example:
https://planetarycomputer.microsoft.com/api/sas/v1/sign?href=https://ukmoeuwest.blob.core.windows.net/deterministic/global/pressure/20260101T0000Z/20260101T0000Z-PT0000H00M-temperature.nc

Additionally, the Planetary Computer's SAS token endpoint allows for the generation of a read-only SAS token that grants access to all assets in the selected collection. For example, to receive a SAS token to access this collection please use:

https://planetarycomputer.microsoft.com/api/sas/v1/token/met-office-global-deterministic-pressure

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