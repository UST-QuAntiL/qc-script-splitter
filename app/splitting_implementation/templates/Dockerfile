FROM python:3.8-slim
LABEL maintainer = "Daniel Vietz <daniel.vietz@iaas.uni-stuttgart.de>"

COPY service.zip /tmp/service.zip

RUN apt-get update && apt-get install -y gcc python3-dev unzip

RUN unzip /tmp/service.zip -d /

RUN pip install -r requirements.txt

CMD python polling_agent.py
