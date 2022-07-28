# Settings

Settings are determined by command line argument, parameters, by environment variables, or by YAML files placed in `~/.pctasks`.

## Profiles

A "profile" tells PCTasks which settings file to use. You can set the profile by setting the `PCTASKS_PROFILE` environment variable, or by using `pctasks profile set ${PROFILE}`.

Profiles allow you to easily switch the environment PCTasks is targeting.

A profile is expected to have a YAML file in the settings folder with the name of the profile. For example, if for the profile `staging`, PCTasks would use the file `~/.pctasks/staging.yaml` for settings.

## Creating profiles

You can create a new profile for the client settings using `pctasks`. Run:

```
> pctasks profile create ${PROFILE}
```
to create a new profile named `${PROFILE}`. Follow the prompts that ask for the API endpoint (e.g. <https://planetarycomputer.microsoft.com/api/tasks/v1>), your API key, and whether or not to ask for confirmation before submitting to the endpoint.

## Editing profiles

You can edit a profile by using `pctasks profile edit ${PROFILE}`, which will take you through the same prompts and default to the values that currently exist in the profile.
