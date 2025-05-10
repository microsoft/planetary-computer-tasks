FROM mcr.microsoft.com/azurelinux/base/python:3.12

RUN tdnf install ca-certificates azure-cli -y \
     && tdnf clean all
ENV PIP_NO_CACHE_DIR=1
RUN pip install "setuptools>=65.5.1"

WORKDIR /opt/src

COPY core /opt/src/core
RUN cd /opt/src/core && \
     pip install .

COPY cli /opt/src/cli
RUN cd /opt/src/cli && \
     pip install .

COPY task /opt/src/task
RUN cd /opt/src/task && \
     pip install .

COPY client /opt/src/client
RUN cd /opt/src/client && \
     pip install .

COPY run /opt/src/run
RUN cd /opt/src/run && \
     pip install .

ENV APP_HOST=0.0.0.0
ENV APP_PORT=81
