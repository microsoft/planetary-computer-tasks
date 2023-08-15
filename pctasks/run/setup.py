"""pctasks: run module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.core>=0.1.0",
    "pctasks.task>=0.1.0",
    "pctasks.client>=0.1.0",
    "azure-batch>=11.0.0,<12",
    "azure-keyvault-secrets>=4.0.0,<5",
    "argo-workflows>=6.3.0,<6.4",
    "networkx>=2.0.0,<3",
    "kubernetes",
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
    name="pctasks.run",
    description="Planetary Computer Tasks framework: Runner component",
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
