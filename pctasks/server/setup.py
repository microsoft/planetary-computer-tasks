"""pctasks: records module."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    desc = f.read()

install_requires = [
    "pctasks.core>=0.1.0",
    "pctasks.run>=0.1.0",
    "fastapi>=0.108.0",
    "python-multipart==0.0.7",
]

extra_reqs = {
    "dev": ["pytest", "pytest-cov", "pre-commit", "httpx"],
    "server": [
        "uvicorn[standard]>=0.12.0,<0.16.0",
    ],
}


setup(
    name="pctasks.server",
    description=("Planetary Computer Tasks framework: Server."),
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
