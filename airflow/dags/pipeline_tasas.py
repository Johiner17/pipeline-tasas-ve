from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# Python y dbt viven en un entorno virtual aparte dentro de la imagen.
PY = "/home/airflow/pipeline_venv/bin/python"
DBT = "/home/airflow/pipeline_venv/bin/dbt"

# Si una tarea falla, Airflow la reintenta 2 veces, con 5 minutos de espera.
# Sirve para fallos temporales, como una fuente que no responde un momento.
argumentos = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="pipeline_tasas_ve",
    description="Tasas de cambio USD/VES: ingesta, carga a raw, dbt run y dbt test",
    # Todos los días a las 22:00, hora de Caracas. La hora es una estimación mía
    # de cuándo ya está publicada la tasa del siguiente día hábil; se puede ajustar.
    schedule="0 22 * * *",
    start_date=pendulum.datetime(2026, 10, 27, tz="America/Caracas"),
    # False: no ejecuta los días anteriores a hoy. Nuestro histórico ya está cargado.
    catchup=False,
    default_args=argumentos,
    tags=["tasas", "venezuela"],
) as dag:

    # 1. Descarga la tasa del día y el histórico y los guarda como JSON crudo.
    ingesta = BashOperator(
        task_id="ingesta",
        bash_command=f"cd /opt/pipeline && {PY} ingesta.py",
    )

    # 2. Carga los JSON nuevos a las tablas del esquema raw.
    carga_raw = BashOperator(
        task_id="carga_raw",
        bash_command=f"cd /opt/pipeline && {PY} cargar_raw.py",
    )

    # 3. Construye staging y marts con dbt.
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd /opt/pipeline/dbt_tasas && {DBT} run --profiles-dir .",
    )

    # 4. Pruebas de calidad. Si fallan, la ejecución del día queda en rojo.
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd /opt/pipeline/dbt_tasas && {DBT} test --profiles-dir .",
    )

    # El orden de ejecución: cada tarea espera a que la anterior termine bien.
    ingesta >> carga_raw >> dbt_run >> dbt_test