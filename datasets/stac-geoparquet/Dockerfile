FROM mcr.microsoft.com/azurelinux/base/python:3.12

# Setup timezone info
ENV TZ=UTC

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV UV_SYSTEM_PYTHON=TRUE

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN tdnf install build-essential jq unzip ca-certificates awk wget curl git azure-cli -y \
     && tdnf clean all

# RUN python3 -m pip install --upgrade pip
RUN pip install --upgrade uv

# Install common packages
COPY requirements-task-base.txt /tmp/requirements.txt
RUN uv pip install --no-build-isolation -r /tmp/requirements.txt

#
# Copy and install packages
#

COPY pctasks/core /opt/src/pctasks/core
RUN cd /opt/src/pctasks/core && \
     uv pip install .

COPY pctasks/cli /opt/src/pctasks/cli
RUN cd /opt/src/pctasks/cli && \
     uv pip install .

COPY pctasks/task /opt/src/pctasks/task
RUN cd /opt/src/pctasks/task && \
     uv pip install .

COPY pctasks/client /opt/src/pctasks/client
RUN cd /opt/src/pctasks/client && \
     uv pip install .

# COPY pctasks/ingest /opt/src/pctasks/ingest
# RUN cd /opt/src/pctasks/ingest && \
#      uv pip install .

# COPY pctasks/dataset /opt/src/pctasks/dataset
# RUN cd /opt/src/pctasks/dataset && \
#      uv pip install .

COPY datasets/stac-geoparquet /opt/src/datasets/stac-geoparquet
RUN uv pip install -r /opt/src/datasets/stac-geoparquet/requirements.txt

# Setup Python Path to allow import of test modules
ENV PYTHONPATH=/opt/src:$PYTHONPATH

WORKDIR /opt/src
