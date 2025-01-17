from airflow import DAG
from airflow.operators.python import PythonOperator

from airflowproject.configs import conf
from airflowproject.functions.dag_functions import submit_job
from airflowproject.functions.task_failure_callback import handle_failure_task

# Define DAG configurations and metadata
dag_id = "recmodel_dag"
default_args = conf.RuntimeConfig.DEFAULT_ARGS
schedule_interval = None
catchup = False  # Prevent running missed executions

# Define the DAG using context manager for readability
with DAG(
    dag_id=dag_id,
    default_args=default_args,
    schedule_interval=schedule_interval,
    catchup=catchup,
) as dag:
    # Define the task with clear structure
    test_recs_model_task = PythonOperator(
        task_id="test_recs_model_task",
        python_callable=submit_job,
        on_failure_callback=handle_failure_task,
    )
