FROM python:3.12-slim-bullseye


ARG API_VERSION
ARG WHEEL=schema_inspector-${API_VERSION}-py3-none-any.whl
RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$WHEEL /code/$WHEEL
RUN pip install --no-cache-dir --upgrade /code/$WHEEL

COPY .env /code/.env
COPY ./templates /code/templates



ENV TEMPLATES_DIR=/code/templates

# Hardcode the app module path directly
CMD uvicorn niagads.schema_inspector_service.core:app --host 0.0.0.0 --port 8000
