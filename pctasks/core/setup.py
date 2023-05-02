"""pctasks: types module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "azure-identity>=1.0.0,<2",
    "azure-storage-blob"
    # https://github.com/microsoft/planetary-computer-tasks/issues/136
    "azure-storage-queue>=12.6.0",
    "azure-data-tables>=12.0.0,<13",
    "azure-cosmos>=4.3.0,<4.4.0",
    "pydantic>=1.9,<2.0.0",
    "orjson>=3.0.0,<4",
    "strictyaml>=1.6",
    "stac-validator>=3.1.0",
    "opencensus-ext-azure==1.1.0",
    "opencensus-ext-logging==0.1.1",
    "pyyaml>=5.3",
    "aiohttp>=3.8.0,<3.9",
    "planetary-computer>=0.4.0",
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
