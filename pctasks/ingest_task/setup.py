"""pctasks: types module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.task>=0.1.0",
    "pctasks.ingest>=0.1.0",
    #"pypgstac==0.4.*",
    "pypgstac @ git+https://github.com/stac-utils/pgstac/@2fef188bfee3c5933619c4d6777a234afbf82028#egg=pypgstac&subdirectory=pypgstac",

    # From pypgstac. Remove when using a release.
    "smart-open==4.2.0",
    "orjson>=3.5.2",
    "python-dateutil==2.8.2",
    "fire==0.4.0",
    "psycopg[binary]==3.*",
    "psycopg-pool==3.*",
    "plpygis==0.2.0",
    "pydantic==1.9.0",
    "tenacity== 8.0.1",
]

extra_reqs = {
    "dev": [
        "pytest",
        "pytest-cov",
        "pre-commit"
    ],
    "docs": ["mkdocs", "mkdocs-material", "pdocs"],
}


setup(
    name="pctasks.ingest_task",
    description="Planetary Computer Tasks framework - Ingest Task.",
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
    author=u"Microsoft",
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
