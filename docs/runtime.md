# Runtime Environment

## Uploading Code

You can make a Python module (a single `.py` file) or package (a possibly nested directory with a `__init__.py` file) available
to the workers executing code by specifying the `code` option on your dataset. The path specified by `code` should be relative to
the `dataset.yaml` or absolute.

```{warning}
This mechanism does *not* ensure that any dependencies are installed. If your module or package
requires additional dependencies beyond what is specified in the `image`, you'll need to
create a new image with those dependencies present.
```

Suppose you have a dataset configuration file `naip/dataset.yaml`, with an accompanying `dataset.py` file. By specifying `code: dataset.py`
that module will be included in the workers runtime.

```yaml
# file: naip/dataset.yaml
naip: naip
image: pctasks-basic:latest
code: dataset.py
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