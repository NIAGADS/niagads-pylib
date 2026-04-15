FROM python:3.12-slim

ARG WHEEL=ragdoc_api_service-0.1.0-py3-none-any.whl


RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$WHEEL /code/$WHEEL
RUN pip install --no-cache-dir --upgrade /code/$WHEEL

COPY .env /code/.env


# FIXME: have to use non-JSON arg to get it to recognize ${TARGET_APP}
CMD uvicorn niagads.ragdoc_service.app:app --host 0.0.0.0 --port 8000