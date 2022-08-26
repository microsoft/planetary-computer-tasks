# Templating

PCTasks uses templating in workflow and dataset YAML to enable dynamic values to be used. This guide describes how templates are
used and what templating functions are available.

## Overview

Templating is used to determine workflow values dynamically. Template expressions are wrapped with `${{` and `}}`, for example

```yaml
src: ${{ local.path(./chesapeake_lulc.py) }}
```

The template values or functions are all grouped with the first term; in the example above, the `path` function is in the
template group `local`. The available groups are described below.

Template substitution can be both processed on the client side, before workflow submission, and on the server side. For example, the `local` functions are evaluated before workflow submission, whereas the `secrets` template expressions are evaluated on the server side to securely inject secrets from Azure KeyVault into task runners.

## Template groups

### args

The `args` group allows access to [](arguments). The argument names are accessed through dot notation, e.g. `args.registry` references the value of the
`registry` argument.

### secrets

...

### item

...

### local

...

### pc

...

