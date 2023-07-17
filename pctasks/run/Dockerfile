FROM python:3.9-slim

ENV CURL_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt
ENV PIP_NO_CACHE_DIR=1

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
