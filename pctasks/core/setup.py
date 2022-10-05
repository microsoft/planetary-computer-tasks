"""pctasks: types module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "azure-identity==1.*",
    "azure-storage-blob==12.9",  # Issues with 12.11 generating sas from account keys
    "azure-storage-queue>=12.*",
    "azure-data-tables==12.*",
    "pydantic>=1.9,<2.0.0",
    "orjson==3.*",
    "strictyaml>=1.6",
    "stac-validator>=3.1.*",
    "opencensus-ext-azure==1.1.0",
    "opencensus-ext-logging==0.1.1",
    "pyyaml>=5.3",
]

extra_reqs = {
    "dev": ["pytest", "pytest-cov", "pre-commit"],
    "docs": ["mkdocs", "mkdocs-material", "pdocs"],
}


setup(
    name="pctasks.core",
    description="Planetary Computer Tasks framework.",
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
    url="https://github.com/Microsoft/planetary-computer-tasks",
    license="MIT",
    packages=find_namespace_packages(exclude=["tests", "scripts"]),
    package_data={"": ["py.typed"]},
    zip_safe=False,
    install_requires=install_requires,
    tests_require=extra_reqs["dev"],
    extras_require=extra_reqs,
)
