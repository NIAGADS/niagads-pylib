# syntax=docker/dockerfile:1

FROM node:alpine as build

ARG REACT_APP_SERVICES_HOST=/services/m

# Install python/pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python \
    && python3 -m ensurepip \
    && pip3 install --no-cache --upgrade pip setuptools 

WORKDIR /app

COPY ./package.json /app/package.json
COPY ./package-lock.json /app/package-lock.json

RUN yarn install
COPY . .
RUN yarn build


FROM nginx
COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html



FROM python:3.10-alpine

WORKDIR /app

ADD requirements.txt .

# install git & python dependencies
RUN pip install --upgrade pip --no-cache-dir \
    && pip install -r /app/requirements.txt --no-cache-dir

ENV SERVICE_PORT=$PORT 

CMD ls /app && gunicorn -w 4 --reload --bind 0.0.0.0:8000 'app:create_app(None)'
