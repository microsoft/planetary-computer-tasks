FROM ubuntu:20.04

# Setup timezone info
ENV TZ=UTC

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y software-properties-common

RUN add-apt-repository ppa:ubuntugis/ppa && \
    apt-get update && \
    apt-get install -y build-essential python3-dev python3-pip \
    jq unzip ca-certificates wget curl git && \
    apt-get autoremove && apt-get autoclean && apt-get clean

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

# See https://github.com/mapbox/rasterio/issues/1289
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Install Python 3.10
RUN curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" \
    && bash "Miniforge3-$(uname)-$(uname -m).sh" -b -p /opt/conda \
    && rm -rf "Miniforge3-$(uname)-$(uname -m).sh"

ENV PATH=/opt/conda/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/conda/lib/:$LD_LIBRARY_PATH

RUN mamba install -y -c conda-forge python=3.10 gdal libgdal-netcdf pip setuptools cython numpy

RUN python -m pip install --upgrade pip

# Install common packages
COPY requirements-task-base.txt /tmp/requirements.txt
RUN python -m pip install --no-build-isolation -r /tmp/requirements.txt

#
# Copy and install packages
#

COPY pctasks/core /opt/src/pctasks/core
RUN cd /opt/src/pctasks/core && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY pctasks/cli /opt/src/pctasks/cli
RUN cd /opt/src/pctasks/cli && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY pctasks/task /opt/src/pctasks/task
RUN cd /opt/src/pctasks/task && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY pctasks/client /opt/src/pctasks/client
RUN cd /opt/src/pctasks/client && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY pctasks/ingest /opt/src/pctasks/ingest
RUN cd /opt/src/pctasks/ingest && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY pctasks/dataset /opt/src/pctasks/dataset
RUN cd /opt/src/pctasks/dataset && \
    pip install -r requirements.txt && \
    pip install --no-deps .

COPY datasets/goes/goes-cmi/requirements.txt /opt/src/datasets/goes/goes-cmi/requirements.txt
RUN python3 -m pip install -r /opt/src/datasets/goes/goes-cmi/requirements.txt
RUN python3 -m pip install rasterio --force-reinstall --no-binary rasterio

# Setup Python Path to allow import of test modules
ENV PYTHONPATH=/opt/src:$PYTHONPATH
# Recent version of GDAL doesn't allow proj.db to be found unless you activate
# the conda environment. This is a workaround to set the PROJ_DATA directory
# unconditionally. Without this, you might see error like:
#    ERROR 1: PROJ: proj_create_from_database: Open of /opt/conda/share/proj failed
# Which indicate the the proj.db file is not found.
# https://proj.org/en/stable/resource_files.html
# You'll know the image works if `gdalsrsinfo epsg:3857` returns WKT.
ENV PROJ_DATA=/opt/conda/share/proj

WORKDIR /opt/src
