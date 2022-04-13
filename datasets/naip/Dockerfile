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
                       jq unzip ca-certificates wget curl && \
    apt-get autoremove && apt-get autoclean && apt-get clean

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

# See https://github.com/mapbox/rasterio/issues/1289
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN python -m pip install --upgrade pip

# Install azure-cli
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

#
# Copy and install packages
#

# TODO: Remove after pgstac release
RUN apt-get install -y git

COPY pctasks/core /opt/lib/pctasks/core
RUN cd /opt/lib/pctasks/core && \
     pip install -e .

COPY pctasks/cli /opt/lib/pctasks/cli
RUN cd /opt/lib/pctasks/cli && \
     pip install -e .

COPY pctasks/task /opt/lib/pctasks/task
RUN cd /opt/lib/pctasks/task && \
     pip install -e .

COPY pctasks/submit /opt/lib/pctasks/submit
RUN cd /opt/lib/pctasks/submit && \
     pip install -e .

COPY pctasks/ingest /opt/lib/pctasks/ingest
RUN cd /opt/lib/pctasks/ingest && \
     pip install -e .

COPY pctasks/dataset /opt/lib/pctasks/dataset
RUN cd /opt/lib/pctasks/dataset && \
     pip install -e .

COPY datasets/naip /opt/src/naip
RUN cd /opt/src/naip && \
     pip install -e .

WORKDIR /opt/src
