# FIXME: when moved to polylith project, use wheel based install
FROM python:3.12-slim

ARG WHEEL=ragdoc_ingestion_service-0.1.0-py3-none-any.whl


RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$WHEEL /code/$WHEEL
RUN pip install --no-cache-dir --upgrade /code/$WHEEL

CMD ["ragdoc-ingestion-worker"]
