ARG registry
FROM ${registry}/pctasks-task-base:latest

COPY datasets/noaa-mrms-qpe /opt/src/datasets/noaa-mrms-qpe
RUN python3 -m pip install -r /opt/src/datasets/noaa-mrms-qpe/requirements.txt
