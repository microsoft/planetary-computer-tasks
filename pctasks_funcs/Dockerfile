FROM mcr.microsoft.com/azure-functions/python:4-python3.10

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

RUN apt update && apt install -y azure-cli

# Copy pctasks packages
COPY pctasks /home/site/pctasks

# Copy function app
COPY pctasks_funcs /home/site/wwwroot

WORKDIR /home/site/wwwroot

RUN pip install -r /home/site/wwwroot/requirements.txt

CMD [ "/home/site/wwwroot/start.sh" ]
