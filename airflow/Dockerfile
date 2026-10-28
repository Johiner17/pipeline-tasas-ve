FROM apache/airflow:3.3.1

USER airflow

# Entorno virtual aparte para nuestro pipeline: así dbt y nuestras
# librerías no chocan con las de Airflow.
RUN python -m venv /home/airflow/pipeline_venv \
 && /home/airflow/pipeline_venv/bin/pip install --no-cache-dir \
    requests "psycopg[binary]" python-dotenv \
    "dbt-core==1.12.6" "dbt-postgres==1.11.0"