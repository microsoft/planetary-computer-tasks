ARG registry
FROM ${registry}/pctasks-task-base:2026.01.12

COPY datasets/noaa-mrms-qpe /opt/src/datasets/noaa-mrms-qpe
RUN python3 -m pip install -r /opt/src/datasets/noaa-mrms-qpe/requirements.txt
