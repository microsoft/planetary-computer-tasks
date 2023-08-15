FROM python:3.9-slim

# Setup timezone info
ENV TZ=UTC

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip

#
# Copy and install packages
#

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

COPY ingest /opt/src/ingest
RUN cd /opt/src/ingest && \
     pip install .

COPY ingest_task /opt/src/ingest_task
RUN cd /opt/src/ingest_task && \
     pip install .

WORKDIR /opt/src
