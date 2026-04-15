FROM python:3.12-slim

ARG WHEEL=ragdoc_admin_service-0.1.0-py3-none-any.whl

RUN python -m pip install --upgrade pip

WORKDIR /app

COPY ./dist/$WHEEL /app/$WHEEL
RUN pip install --no-cache-dir --upgrade /app/$WHEEL

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "-m", "niagads.ragdoc_admin_service.streamlit_app", "--server.port=8501", "--server.address=0.0.0.0"]

