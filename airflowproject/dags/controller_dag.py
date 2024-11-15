"""
This module defines a controller DAG for triggering other DAGs dynamically
based on a configuration file provided at runtime. The DAG's configuration
is stored in an external YAML file, and its path is passed as a parameter
to the DAG. The configuration determines which DAGs to trigger and with what
parameters.
"""

from datetime import datetime

import pytz
import yaml
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

from airflowproject.configs import conf

# Constants
CONFIG_FILE_PATH_PARAM = "config_file_path"
TRIGGER_RULE_DONE = "all_done"
POKE_INTERVAL_SEC = 1
TAGS_CONTROLLER = ["controller"]
SCHEDULE_INTERVAL_NONE = None
MAX_ACTIVE_RUNS = 1
CATCHUP = False


@task
def save_dag_run_config(**context):
    """
    Save the configuration file path to XCom.

    This function extracts the configuration file path from the DAG run
    parameters and saves it both to an Airflow Variable and to XCom for
    downstream tasks to access.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    None
    """
    # Get DAG parameters from the context
    dag_params = context["dag_run"].conf or {}  # Use .conf for parameters
    config_file_path = dag_params.get(CONFIG_FILE_PATH_PARAM)
    if config_file_path:
        # Save the configuration file path as an Airflow Variable
        Variable.set(CONFIG_FILE_PATH_PARAM, config_file_path)
        # Push the config path to XCom for downstream tasks
        ti = context["ti"]
        ti.xcom_push(key=CONFIG_FILE_PATH_PARAM, value=config_file_path)


@task
def load_dag_configuration(**context):
    """
    Load the DAG configuration from a YAML file.

    This function retrieves the configuration file path from XCom or an
    Airflow Variable, then reads the YAML configuration file to load the
    configuration.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    dict: The DAG configuration loaded from the YAML file.

    Raises:
    FileNotFoundError: If the configuration file does not exist.
    yaml.YAMLError: If there is an error in reading the YAML configuration.
    """
    # Access TaskInstance (TI) and pull the config path from XCom
    ti = context["ti"]
    config_file_path = ti.xcom_pull(
        task_ids="save_dag_run_config", key=CONFIG_FILE_PATH_PARAM
    )
    if not config_file_path:
        # Fallback to Airflow Variable if not found in XCom
        config_file_path = Variable.get(CONFIG_FILE_PATH_PARAM)
    # Load the YAML configuration
    with open(config_file_path, "r") as file:
        print(config_file_path)
        dag_info = yaml.safe_load(file)
    # Return the DAG configuration to be available via XCom
    return dag_info


@task
def trigger_dag_tasks(**context):
    """
    Retrieve configuration and trigger DAGs dynamically.

    This function reads the configuration from XCom, iterates over the
    configuration entries, and triggers the respective DAGs dynamically
    using the `TriggerDagRunOperator`.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    None

    Raises:
    ValueError: If the configuration is not loaded properly.
    """
    # Retrieve the loaded configuration from XCom
    ti = context["ti"]
    config = ti.xcom_pull(task_ids="load_dag_configuration")
    if not config:
        # Raise an error if the configuration couldn't be loaded
        raise ValueError("Failed to load DAG configuration.")
    local_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    # Iterate over each scheduled DAG in the configuration
    for scheduled_dag_id, parameters in config.items():
        execution_time = parameters.get("execution_time")
        try:
            # Trigger DAGs dynamically based on the configuration
            if execution_time is None:
                TriggerDagRunOperator(
                    task_id=f"trigger_{scheduled_dag_id}",
                    trigger_dag_id=scheduled_dag_id,
                    conf=parameters.get("params", {}),
                    execution_date=datetime.now(local_tz).strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                    wait_for_completion=True,
                    poke_interval=POKE_INTERVAL_SEC,
                    trigger_rule=TRIGGER_RULE_DONE,
                    reset_dag_run=True,
                ).execute(context)
            else:
                TriggerDagRunOperator(
                    task_id=f"trigger_{scheduled_dag_id}",
                    trigger_dag_id=scheduled_dag_id,
                    execution_date=execution_time,
                    conf=parameters.get("params", {}),
                    wait_for_completion=True,
                    reset_dag_run=True,
                    poke_interval=POKE_INTERVAL_SEC,
                    trigger_rule=TRIGGER_RULE_DONE,
                ).execute(context)
        except Exception as e:
            # Log the exception and continue with the next DAG
            ti.log.error(f"Failed to trigger DAG {scheduled_dag_id}: {e}")


# DAG Definition

with DAG(
    dag_id="controller_dag",
    schedule_interval=conf.ScheduleConfig.CONTROLLER_DAG_SCHEDULE,
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    params={CONFIG_FILE_PATH_PARAM: None},
) as dag:
    # Dummy start task
    start_task = DummyOperator(task_id="start")
    # Task to save configuration to XCom
    save_config_task = save_dag_run_config()
    # Task to load the configuration
    load_config_task = load_dag_configuration()
    # Task to trigger the DAGs dynamically
    trigger_tasks_task = trigger_dag_tasks()
    # Define dependencies
    start_task >> save_config_task >> load_config_task >> trigger_tasks_task
