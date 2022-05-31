FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y build-essential git

ENV CURL_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt

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

COPY submit /opt/src/submit
RUN cd /opt/src/submit && \
     pip install .

COPY run /opt/src/run
RUN cd /opt/src/run && \
     pip install .

ENV APP_HOST=0.0.0.0
ENV APP_PORT=81
