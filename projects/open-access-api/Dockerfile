FROM python:3.12-slim-bullseye

ARG API_VERSION
ARG WHEEL=open_access_api-${API_VERSION}-py3-none-any.whl

RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$WHEEL /code/$WHEEL
RUN pip install --no-cache-dir --upgrade /code/$WHEEL

COPY .env /code/.env

CMD ["uvicorn", "niagads.open_access_api.core:app", "--host", "0.0.0.0", "--port", "8000"]