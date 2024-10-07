FROM mcr.microsoft.com/cbl-mariner/base/python:3.9

RUN tdnf install -y ca-certificates build-essential git \
    && tdnf clean all

ARG DEVELOPMENT=FALSE

ENV PIP_NO_CACHE_DIR=1
RUN pip install "setuptools>=65.5.1"

WORKDIR /opt/src

COPY core /opt/src/core
RUN cd /opt/src/core && \
     pip install .

COPY cli /opt/src/cli
RUN cd /opt/src/cli && \
     pip install .

COPY client /opt/src/client
RUN cd /opt/src/client && \
     pip install .

COPY task /opt/src/task
RUN cd /opt/src/task && \
     pip install .

COPY run /opt/src/run
RUN cd /opt/src/run && \
     pip install .

COPY server /opt/src/server
RUN cd /opt/src/server && \
     pip install .[server]

RUN if [ "${DEVELOPMENT}" = "TRUE" ]; then \
     echo "INSTALLING DEVELOPMENT DEPENDENCIES"; \
     yum install -y azure-cli; \
     pip install \
     -e /opt/src/core \
     -e /opt/src/cli \
     -e /opt/src/client \
     -e /opt/src/task \
     -e /opt/src/run \
     -e /opt/src/server[dev,server]; \
    fi

ENV APP_HOST=0.0.0.0
ENV APP_PORT=81

CMD uvicorn pctasks.server.main:app --host ${APP_HOST} --port ${APP_PORT} --log-level info
