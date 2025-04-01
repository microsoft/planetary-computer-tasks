FROM mcr.microsoft.com/azurelinux/base/python:3.12

# Setup timezone info
ENV TZ=UTC

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN tdnf install build-essential jq unzip ca-certificates awk wget curl git azure-cli -y \
    && tdnf clean all

# Install GDAL through conda
# Rasterio doesn't make `gdal_translate` available
# and the stactools package depends on calling `gdal_translate`.
RUN mkdir -p ~/miniconda3 \
    && wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh \
    && chmod +x ~/miniconda3/miniconda.sh

# Do we need all of these?
RUN bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 \ 
    && rm ~/miniconda3/miniconda.sh \
    && source ~/miniconda3/bin/activate \ 
    && conda install -c conda-forge sqlite gdal libgdal \
    libgdal-arrow-parquet libgdal-avif \
    libgdal-core \
    libgdal-fits libgdal-grib \ 
    libgdal-hdf4 libgdal-hdf5 libgdal-heif libgdal-jp2openjpeg \
    libgdal-kea libgdal-netcdf libgdal-pdf libgdal-pg libgdal-postgisraster \
    libgdal-tiledb libgdal-xls

# Put all the GDAL tools in PATH
ENV PATH=/root/miniconda3/bin:$PATH
# Help the loader
ENV LD_LIBRARY_PATH=/root/miniconda3/lib:$LD_LIBRARY_PATH

# Install common packages
COPY requirements-task-base.txt /tmp/requirements.txt
RUN pip install --no-build-isolation -r /tmp/requirements.txt

COPY pctasks/core /opt/src/pctasks/core
RUN cd /opt/src/pctasks/core && \
    pip install .

COPY pctasks/cli /opt/src/pctasks/cli
RUN cd /opt/src/pctasks/cli && \
    pip install .

COPY pctasks/task /opt/src/pctasks/task
RUN cd /opt/src/pctasks/task && \
    pip install .

COPY pctasks/client /opt/src/pctasks/client
RUN cd /opt/src/pctasks/client && \
    pip install .

COPY pctasks/ingest /opt/src/pctasks/ingest
RUN cd /opt/src/pctasks/ingest && \
    pip install .

COPY pctasks/dataset /opt/src/pctasks/dataset
RUN cd /opt/src/pctasks/dataset && \
    pip install .

COPY datasets/goes/goes-cmi/requirements.txt /opt/src/datasets/goes/goes-cmi/requirements.txt
RUN pip install -r /opt/src/datasets/goes/goes-cmi/requirements.txt

# Setup Python Path to allow import of test modules
ENV PYTHONPATH=/opt/src:$PYTHONPATH

WORKDIR /opt/src