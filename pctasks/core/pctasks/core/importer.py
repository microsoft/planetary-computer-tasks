"""
Import machinery for loading code from Azure Blob Storage.
"""
# Simple / explicit mechanism for importing a module or zipped package from
# a URI. In the future, we might implement a more advanced mechanism that
# would directly hook into the `import` statement.
# For background, checkout out Recipe 10.11 in the Python Cookbook (3rd edition)
from __future__ import annotations

import logging
import pathlib
import site
import subprocess
import sys
import zipfile
from tempfile import TemporaryDirectory
from typing import List, Optional

from pctasks.core.storage import Storage

logger = logging.getLogger(__name__)


def ensure_requirements(
    requirements_path: str,
    storage: Storage,
    pip_options: Optional[List[str]] = None,
    target_dir: Optional[str] = None,
) -> None:
    """
    Ensure that the requirements at ``requirements_path`` are available.

    Parameters
    ----------
    requirements_path: str
        Path to a pip requirements file
    pip_options: list[str]
        Optional arguments to pass to the command ``pip install -r``.
    """
    with TemporaryDirectory() as tmp_dir:
        local_path = str(pathlib.Path(tmp_dir) / pathlib.Path(requirements_path).name)
        storage.download_file(requirements_path, local_path)
        pip_options = pip_options or []
        if target_dir:
            if "-t" in pip_options or "--target" in pip_options:
                raise ValueError(
                    "Cannot specify target directory in pip options; "
                    f"target directory already specified as {target_dir}"
                )
            target_dir_path = pathlib.Path(target_dir)
            target_dir_path.mkdir(parents=True, exist_ok=True)
            resolved_dir = str(target_dir_path.resolve())
            pip_options.extend(["-t", resolved_dir])
            if resolved_dir not in sys.path:
                sys.path = [resolved_dir] + sys.path
        logger.debug("Pip installing from %s", requirements_path)
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            local_path,
        ] + pip_options

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate()
        returncode = proc.wait()
        if returncode:
            logger.error("Pip install failed with %s", stderr.decode().strip())
            raise subprocess.CalledProcessError(returncode, cmd, stdout, stderr)
        logger.debug("Pip install output: %s", stdout.decode().strip())


def ensure_code(
    file_path: str,
    storage: Storage,
    is_package: bool | None = None,
    target_dir: Optional[str] = None,
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

        When ``is_package`` is true, the path is appended to ``sys.path``, and
        submodules can be imported from that package.
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
    if target_dir:
        target_dir_path = pathlib.Path(target_dir)
        target_dir_path.mkdir(parents=True, exist_ok=True)
        resolved_dir = str(target_dir_path.resolve())
        if resolved_dir not in sys.path:
            sys.path = [resolved_dir] + sys.path
        output_path = pathlib.Path(target_dir) / pathlib.Path(file_path).name
    else:
        output_path = (
            pathlib.Path(site.getsitepackages()[0]) / pathlib.Path(file_path).name
        )

    if output_path.exists():
        logger.debug("Module destination %s already exists", output_path)

    storage.download_file(file_path, str(output_path))

    if is_package is None:
        is_package = zipfile.is_zipfile(output_path)
    if is_package:
        logger.debug("Adding %s to sys.path", output_path)
        sys.path.append(str(output_path))

    return pathlib.Path(output_path)
