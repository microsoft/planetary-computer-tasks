FROM pccomponentstest.azurecr.io/pctasks-task-base

COPY ./datasets/nex-cddp-cmip6/requirements.txt /opt/src/datasets/nex-cddp-cmip6/requirements.txt
RUN python3 -m pip install -r /opt/src/datasets/nex-cddp-cmip6/requirements.txt

# Setup Python Path to allow import of test modules
ENV PYTHONPATH=/opt/src:$PYTHONPATH

WORKDIR /opt/src