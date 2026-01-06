This collection offers 1 parameter at 33 available height levels (5m to 6000m) from the Met Office global deterministic 10km forecast. This is a numerical weather prediction forecast for the whole globe, with a resolution of approximately 0.09 degrees i.e. 10km (2,560 x 1,920 grid points). 

The data is available as NetCDF files. It's offered on a free, unsupported basis, so we don’t recommend using it for any critical business purposes.

## Height Levels
Available height levels, in metres (m) above ground, are: 
* 5.0 10.0 20.0 30.0 50.0 75.0 100.0 150.0 200.0 250.0 300.0 400.0 500.0 600.0 700.0 800.0 1000.0 1250.0 1500.0 1750.0 2000.0 2250.0 2500.0 2750.0 3000.0 3250.0 3500.0 3750.0 4000.0 4500.0 5000.0 5500.0 6000.0

## Timesteps
The following timesteps are available:
* every hour from 0 to 54 hours
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

## How to cite
Met Office global deterministic 10km forecast was accessed on DATE from the Microsoft Planetary Computer (https://zenodo.org/records/7261897).

## License
British Crown copyright 2023-2025, the Met Office, is licensed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/deed.en).

## Providers
[Met Office](https://www.metoffice.gov.uk/)
See all datasets managed by [Met Office.](https://registry.opendata.aws/?search=managedBy:met%20office)

## Contact
[servicedesk@metoffice.gov.uk](mailto:servicedesk@metoffice.gov.uk). Service desk is only available Mon – Fri, 09:00 until 17:00 UTC (-1 hour during BST). As a non-operational service we aim to respond to any service support enquiries within 3-5 business days. 