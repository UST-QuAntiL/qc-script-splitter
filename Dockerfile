FROM python:3.9-slim

MAINTAINER Daniel Vietz "daniel.vietz@iaas.uni-stuttgart.de"

WORKDIR /app
RUN apt-get update
RUN apt-get install -y gcc python3-dev
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app

EXPOSE 5013/tcp

ENV FLASK_APP=script-splitter.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=0
RUN echo "python -m flask db upgrade" > /app/startup.sh
RUN echo "gunicorn script-splitter:app -b 0.0.0.0:5013 -w 4 --timeout 500 --log-level info" >> /app/startup.sh
CMD [ "sh", "/app/startup.sh" ]
