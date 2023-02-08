"""pctasks.ingest: Ingestion messages and submission."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.client>=0.1.0",
    "jinja2==3.0.3",
    "marko==1.0.1",
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
    name="pctasks.ingest",
    description="Planetary Computer Tasks framework - Ingest",
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
    use_scm_version={
        "root": "../..",
    },
    setup_requires=["setuptools_scm"],
)
