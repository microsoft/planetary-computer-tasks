"""
Import machinery for loading code from Azure Blob Storage.
"""
# Simple / explicit mechanism for importing a module or zipped package from
# a URI. In the future, we might implement a more advanced mechanism that
# would directly hook into the `import` statement.
# For background, checkout out Recipe 10.11 in the Python Cookbook (3rd edition)
from __future__ import annotations

import sys
import site
import pathlib
import logging
import zipfile

import pctasks.core.storage

logger = logging.getLogger(__name__)


def ensure_code(
    file_path: str,
    storage: pctasks.core.storage.Storage,
    is_package: bool | None = None,
) -> pathlib.Path:
    """
    Ensure that a module or zipped package at a URI ``file_path`` is importable.

    Parameters
    ----------
    file_path : str
        The path to the file (relative to the ``storage`` filesystem).
    storage:
        The storage object used to access the file
    is_package: bool, optional
        Whether to treat this file as a Python package. By default, this is inferred
        by calling :func:`zipfile.is_zipfile`.

        When ``is_package`` is true, the path is appended to ``sys.path``, and submodules
        can be imported from that package.
    Returns
    -------
    pathlib.Path
        The path of the downloaded file. This will typically be in the ``site-packages``
        directory.

    Notes
    -----
    See `PyZipFile <https://docs.python.org/3/library/zipfile.html#pyzipfile-objects>`_
    for more on creating Zip files for Python packages.

    """
    output_path = pathlib.Path(site.getsitepackages()[0]) / pathlib.Path(file_path).name
    if output_path.exists():
        logger.debug("Module destination %s already exists", output_path)

    storage.download_file(file_path, output_path)

    if is_package is None:
        is_package = zipfile.is_zipfile(output_path)
    if is_package:
        logger.debug("Adding %s to sys.path", output_path)
        sys.path.append(str(output_path))
