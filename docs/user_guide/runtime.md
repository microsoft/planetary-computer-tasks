# Runtime Environment

## Specifying requirements

In addition to the set of packages provided by the base docker image, you can specify a list of additional packages
to install with a `requirements.txt` file. This can be done in a dataset configuration or in a task configuration.

```yaml
# file: naip/dataset.yaml
name: naip
image: pctasks-basic:latest
code:
  requirements: ${{ local.path("requirements.txt") }}
```

This should be a text file following Pip's [requirements file format](https://pip.pypa.io/en/latest/reference/requirements-file-format/).

```
# file: naip/requirements.txt
git+https://github.com/stactools-packages/naip@dd703d010115b400e45ae8b1ca18816966e38231
```

The path specified in `code.requirements` should be relative to the `dataset.yaml`.

## Uploading Code

You can make a Python module (a single `.py` file) or package (a possibly nested directory with a `__init__.py` file) available
to the workers executing code by specifying the `code.src` option on your dataset. The path specified by `code.src` should be relative to
the `dataset.yaml` using the ``local.path(relative_path)`` templater or an absolute path.

Suppose you have a dataset configuration file `naip/dataset.yaml`, with an accompanying `dataset.py` file. By setting the `code.src` option to `dataset.py`
that module will be included in the workers runtime.

```yaml
# file: naip/dataset.yaml
name: naip
image: pctasks-basic:latest
code:
  src: ${{ local.path(dataset.py) }}
```

For single-file modules, the module will be importable using the name of the module: `import dataset` in this case.

Packages are importable using the name of the top-level directory. Given a layout like

```python
mypackage/
  __init__.py
  module_a.py
  module_b.py
```

Your code is importable with `import mypackage`, `from mypackage import module_a`, etc.

Behind the scenes, when you submit a workflow generated from this `dataset.yaml`
the module is uploaded to Azure Blob Storage. Before executing your task, the
worker downloads that module and places it in a location that's importable by
the Python interpreter.