# syntax=docker/dockerfile:1

FROM python:slim-bookworm AS builder

ARG BUILD

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install git to be able to fetch niagads-pylib from git
RUN apt-get update && apt-get install --no-install-recommends -y \
    git \
    # remove cache
    && apt autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list

RUN python -m venv /opt/venv

# ensure venv is used; see https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
# to understand how this "activates" the venv
ENV PATH="/opt/venv/bin:$PATH"

# Install application
WORKDIR /init

COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt 