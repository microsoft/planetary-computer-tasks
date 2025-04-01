FROM mcr.microsoft.com/azurelinux/base/python:3.12

RUN tdnf install -y ca-certificates build-essential git \
    && tdnf clean all

ARG DEVELOPMENT=FALSE

ENV PIP_NO_CACHE_DIR=1
RUN pip install "setuptools>=65.5.1" uv

WORKDIR /opt/src

COPY core /opt/src/core
RUN cd /opt/src/core && \
     uv pip install --system --no-deps .

COPY cli /opt/src/cli
RUN cd /opt/src/cli && \
     uv pip install --system --no-deps .

COPY client /opt/src/client
RUN cd /opt/src/client && \
     uv pip install --system --no-deps .

COPY task /opt/src/task
RUN cd /opt/src/task && \
     uv pip install --system --no-deps .

COPY run /opt/src/run
RUN cd /opt/src/run && \
     uv pip install --system --no-deps .

COPY server /opt/src/server
RUN cd /opt/src/server && \
     uv pip install --system -r requirements.txt && \
     uv pip install --system --no-deps .[server]

RUN if [ "${DEVELOPMENT}" = "TRUE" ]; then \
     echo "INSTALLING DEVELOPMENT DEPENDENCIES"; \
     yum install -y azure-cli; \
     uv pip install --system \
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
