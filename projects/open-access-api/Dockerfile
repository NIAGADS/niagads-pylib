FROM python:3.12-slim-bullseye

ARG API_VERSION
ARG WHEEL=open_access_api-${API_VERSION}-py3-none-any.whl
ARG APP_MODULE

RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$WHEEL /code/$WHEEL
RUN pip install --no-cache-dir --upgrade /code/$WHEEL

COPY .env /code/.env

ENV TARGET_APP=${APP_MODULE}

# FIXME: have to use non-JSON arg to get it to recognize ${TARGET_APP}
CMD uvicorn ${TARGET_APP} --host 0.0.0.0 --port 8000