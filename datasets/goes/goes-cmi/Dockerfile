FROM mcr.microsoft.com/azurelinux/base/python:3.12

# Setup timezone info
ENV TZ=UTC

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN tdnf install build-essential jq unzip ca-certificates awk wget curl git azure-cli -y \
    && tdnf clean all

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