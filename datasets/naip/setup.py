"""pctasks: types module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.core>=0.1.0",
    "pctasks.submit>=0.1.0",
    "pctasks.ingest>=0.1.0",
    "pctasks.cli>=0.1.0",
    "pctasks.dataset>=0.1.0",
    (
        "stactools-naip @ git+https://github.com/stactools-packages/"
        "naip.git#egg=stactools-naip"
    ),
]

setup(
    name="pctasks.datasets.naip",
    description="PCTasks dataset - NAIP",
    long_description=desc,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="Planetary, STAC",
    author="Microsoft",
    author_email="planetarycomputer@microsoft.com",
    url="https://github.com/Microsoft/pctasks-naip",
    license="MIT",
    packages=find_namespace_packages(exclude=["tests", "scripts"]),
    package_data={"": ["py.typed"]},
    zip_safe=False,
    install_requires=install_requires,
)
