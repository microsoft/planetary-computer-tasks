# Settings

Settings are determined by command line argument, parameters, by environment variables, or by YAML files placed in `~/.pctasks`.

## Profiles

A "profile" tells PCTasks which settings file to use. You can set the profile by setting the `PCTASKS_PROFILE` environment variable, or by using `pctasks profile set ${PROFILE}`.

Profiles allow you to easily switch the environment PCTasks is targeting.

A profile is expected to have a YAML file in the settings folder with the name of the profile. For example, if for the profile `staging`, PCTasks would use the file `~/.pctasks/staging.yaml` for settings.

### Creating profiles

You can create a new profile for the client settings using `pctasks`. Run:

```
> pctasks profile create ${PROFILE}
```
to create a new profile named `${PROFILE}`. Follow the prompts that ask for the API endpoint (e.g. <https://planetarycomputer.microsoft.com/api/tasks/v1>), your API key, and whether or not to ask for confirmation before submitting to the endpoint.

### Editing profiles

You can edit a profile by using `pctasks profile edit ${PROFILE}`, which will take you through the same prompts and default to the values that currently exist in the profile.

## Client Settings

PCTask users will need to specify client settings for usage. A settings file created by the above commands looks like this:

```
client:
  endpoint: https://planetarycomputer-staging.microsoft.com/api/tasks/v1
  api_key: XXXXXX
  confirmation_required: true
  default_args:
    registry: pccomponents.azurecr.io
```

The endpoint is the PCTasks API endpoint, and the API Key is the API Management token that is used to authenticate against the API.

If `confirmation_required` is true, PCTasks will ask for confirmation before submitting workflows to the endpoint. This can provide a double-check to ensure the intended profile is being used.

`default_args` allows a profile to specify default arguments for workflows. This is useful for common arguments in workflows, such as the container registry that should be used to pull a task image. In the above example, the user would not have to specify the `registry` argument when using the profile with these settings as they will be supplied by the defaults. Note that an argument is specified on the command line, will take precedence over a settings default.

## Frontend Settings

To run locally, the frontend will need separate configuration settings for the API endpoint and the API key. In the `pctasks_frontend` directory, copy .env.example to .env and update the values to match your environment.
