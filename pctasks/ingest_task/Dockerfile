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

RUN apt-get install -y git

COPY core /opt/src/core
RUN cd /opt/src/core && \
     pip install .

COPY cli /opt/src/cli
RUN cd /opt/src/cli && \
     pip install .

COPY task /opt/src/task
RUN cd /opt/src/task && \
     pip install .

COPY submit /opt/src/submit
RUN cd /opt/src/submit && \
     pip install .

COPY ingest /opt/src/ingest
RUN cd /opt/src/ingest && \
     pip install .

COPY ingest_task /opt/src/ingest_task
RUN cd /opt/src/ingest_task && \
     pip install .

#
# Environment configuration
#

# Setup Python Path
ENV PYTHONPATH=/opt/src:$PYTHONPATH

# Force SSL for Postgres
ENV PGSSLMODE=require

WORKDIR /opt/src
