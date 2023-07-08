# syntax=docker/dockerfile:1

FROM python:3.10-alpine

WORKDIR /app

ADD requirements.txt .

# install git & python dependencies
RUN pip install --upgrade pip --no-cache-dir \
    && pip install -r /app/requirements.txt --no-cache-dir

ENV SERVICE_PORT=$PORT 

CMD ls /app && gunicorn -w 4 --reload --bind 0.0.0.0:8000 'app:create_app(None)'
