FROM python:3.12-slim

ARG WHEEL=metadata_builder-0.1.0-py3-none-any.whl
ARG APP_MODULE=niagads.genomicsdb_service.utilities.track_metadata_builder.app

RUN python -m pip install --upgrade pip

WORKDIR /app

COPY ./dist/$WHEEL /app/$WHEEL
RUN pip install --no-cache-dir --upgrade /app/$WHEEL

COPY ontology_reference.txt .
COPY streamlit_app.py .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

