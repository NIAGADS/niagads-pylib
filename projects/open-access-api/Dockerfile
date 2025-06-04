FROM python:3.12.10-slim-bullseyes

ARG wheel=open-access-api-0.1.0-py3-none-any.whl

RUN python -m pip install --upgrade pip

WORKDIR /code

COPY ./dist/$wheel /code/$wheel
RUN pip install --no-cache-dir --upgrade /code/$wheel

CMD ["uvicorn", "niagads.open_access_api.core:app", "--host", "0.0.0.0", "--port", "8000"]