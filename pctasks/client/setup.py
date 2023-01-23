"""pctasks: client module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.core>=0.1.0",
    "pctasks.cli>=0.1.0",
    "pydantic[dotenv]>=1.8,<2.0.0",
    "rich==11.2.0",
]

extra_reqs = {
    "dev": ["pytest", "pytest-cov", "pre-commit"],
    "docs": ["mkdocs", "mkdocs-material", "pdocs"],
}


setup(
    name="pctasks.client",
    description="Planetary Computer Tasks framework - Client.",
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
