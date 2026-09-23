FROM apache/airflow:2.9.1-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
USER airflow
COPY pyproject.toml /tmp/pyproject.toml
COPY src /opt/airflow/src
RUN pip install --no-cache-dir -e /opt/airflow/src \
    && pip install --no-cache-dir apache-airflow-providers-postgres "dbt-postgres>=1.7"
